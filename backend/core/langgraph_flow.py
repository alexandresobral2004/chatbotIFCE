import os
import re
from typing import List, Optional, Dict, Any, Callable
from langgraph.graph import StateGraph, START, END

from .state import AgentState
from .prompts import ROUTER_PROMPT, QUERY_OPTIMIZER_PROMPT, GRADER_PROMPT, GENERATOR_PROMPT, CITATION_PROMPT, GUARDRAIL_PROMPT, HALLUCINATION_PROMPT
from .application.jev_judgments import (
    RELEVANCE_THRESHOLD,
    GROUNDED_THRESHOLD,
    INJECTION_THRESHOLD,
    grade_documents,
    grounded_probability,
    injection_probability,
)

# Palavra inteira: "dan" nao pode casar com "mudanca" ou "cidadania".
INJECTION_KEYWORDS_RE = re.compile(r"\b(?:ignore|forget|bypass|pirate|system prompt|dan)\b")

# Node implementations that receive state and optionally external ports

class GuardrailNode:
    """Detects prompt injection or bypassing attempts."""

    async def __call__(self, state: AgentState) -> AgentState:
        query = state.get("user_message", "").lower()
        llm = state.get("_validator_llm") or state.get("_llm_provider")
        new_state = state.copy()
        
        # Simple heuristic + LLM check
        if INJECTION_KEYWORDS_RE.search(query):
            new_state["is_injection"] = True
            new_state["final_response"] = "Desculpe, não posso processar essa solicitação pois viola as diretrizes de segurança acadêmica."
            return new_state
            
        p_injection = await injection_probability(state.get("_judge"), state.get("user_message", ""))
        if p_injection is not None:
            if p_injection >= INJECTION_THRESHOLD:
                new_state["is_injection"] = True
                new_state["final_response"] = "Desculpe, não posso processar essa solicitação pois viola as diretrizes de segurança acadêmica."
                return new_state
            new_state["is_injection"] = False
            return new_state

        if llm:
            messages = [
                {"role": "system", "content": GUARDRAIL_PROMPT},
                {"role": "user", "content": query}
            ]
            try:
                response = ""
                async for chunk in llm.chat(messages, max_tokens=10, temperature=0.0, stream=True):
                    response += chunk
                
                if "INJECTION" in response.upper():
                    new_state["is_injection"] = True
                    new_state["final_response"] = "Desculpe, não posso processar essa solicitação pois viola as diretrizes de segurança acadêmica."
                    return new_state
            except Exception:
                pass

        new_state["is_injection"] = False
        return new_state


class RefusalNode:
    """Handles cases where no relevant documents were found."""

    async def __call__(self, state: AgentState) -> AgentState:
        new_state = state.copy()
        new_state["final_response"] = (
            "Não encontrei evidências suficientes no Manual ou na base de dados para "
            "responder a esta pergunta com precisão acadêmica. Você poderia reformular "
            "ou fornecer mais detalhes?"
        )
        return new_state


class HallucinationCheckerNode:
    """Verifies if the generated answer is grounded in retrieved docs."""

    async def __call__(self, state: AgentState) -> AgentState:
        llm = state.get("_validator_llm") or state.get("_llm_provider")
        docs = state.get("retrieved_docs", [])
        response = state.get("final_response", "")
        new_state = state.copy()

        if not docs or not response:
            new_state["is_hallucination"] = False
            return new_state

        p_grounded = await grounded_probability(state.get("_judge"), response, docs)
        if p_grounded is not None:
            new_state["is_hallucination"] = p_grounded < GROUNDED_THRESHOLD
            if new_state["is_hallucination"]:
                new_state["final_response"] += "\n\n**Aviso:** Parte desta resposta pode não estar estritamente contida nas referências bibliográficas consultadas."
            return new_state

        if not llm:
            new_state["is_hallucination"] = False
            return new_state

        context = "\n\n".join([d.get("content", "") for d in docs])
        messages = [
            {"role": "system", "content": HALLUCINATION_PROMPT},
            {"role": "user", "content": f"Contexto:\n{context}\n\nResposta Gerada:\n{response}"}
        ]

        try:
            check_result = ""
            async for chunk in llm.chat(messages, max_tokens=10, temperature=0.0, stream=True):
                check_result += chunk
            
            if "HALLUCINATION" in check_result.upper():
                new_state["is_hallucination"] = True
                new_state["final_response"] += "\n\n**Aviso:** Parte desta resposta pode não estar estritamente contida nas referências bibliográficas consultadas."
            else:
                new_state["is_hallucination"] = False
        except Exception:
            new_state["is_hallucination"] = False

        return new_state

class RouterNode:
    """Decides whether to retrieve or optimise the query."""

    # Saudações, agradecimentos e conversa leve que não precisam de retrieval
    GREETING_KEYWORDS = [
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", "e aí", "eai",
        "hey", "hello", "hi", "tudo bem", "como vai", "obrigado", "obrigada",
        "valeu", "vlw", "brigado", "brigada", "quem e voce", "quem é você",
        "o que voce faz", "o que você faz", "pode me ajudar", "me ajuda",
    ]

    async def __call__(self, state: AgentState) -> AgentState:
        query = state.get("user_message", "").lower().strip()

        # Conversationa leve: saudação/agradecimento -> resposta amigável sem retrieval
        if any(g in query for g in self.GREETING_KEYWORDS):
            new_state = state.copy()
            new_state["is_greeting"] = True
            new_state["final_response"] = (
                "Olá! 😊 Sou o Professor Doutor em Metodologia Científica e "
                "Normalização Acadêmica. Estou aqui para ajudar você com "
                "metodologia científica, normas da ABNT/APA e estruturação de "
                "trabalhos acadêmicos (TCC, artigos, monografias).\n\n"
                "📚 Para começar, me conte: **qual é a área do seu trabalho** e o que "
                "você gostaria de aprender ou formatar? Assim consigo trazer exemplos "
                "práticos e referências na norma certa para o seu caso."
            )
            new_state["_route"] = "END"
            return new_state

        # Simple heuristic-based routing
        technical_keywords = [
            "python", "java", "react", "api", "database", "code",
            "algorithm", "function", "class", "error", "debug",
            "langchain", "langgraph", "llm", "vector", "embedding",
            "abnt", "nbr", "citacao", "referencia", "metodologia", "tcc",
            "artigo", "pibic", "finep", "lattes", "cnpq", "capes", "scielo",
        ]
        is_technical = any(kw in query for kw in technical_keywords)

        new_state = state.copy()
        new_state["is_greeting"] = False
        new_state["optimized_query"] = None
        new_state["_route"] = "OPTIMIZE" if is_technical else "RETRIEVE"
        return new_state


class OptimizerNode:
    """Generates a refined query using domain-specific academic & technical vocabulary."""

    async def __call__(self, state: AgentState) -> AgentState:
        new_state = state.copy()
        user_msg = state.get("user_message", "")
        new_state["optimized_query"] = f"academic research query: {user_msg}"
        return new_state


class RetrieverNode:
    """Retrieves relevant documents using the vector store port."""

    async def __call__(self, state: AgentState) -> AgentState:
        vector_repo = state.get("_vector_repository")
        query = state.get("optimized_query") or state.get("user_message", "")

        if vector_repo is None:
            return state

        try:
            docs = await vector_repo.search_similar_chunks(query, limit=5, threshold=0.5)
            new_state = state.copy()
            new_state["retrieved_docs"] = [
                {"id": f"doc_{i}", "content": doc, "score": 1.0 - i * 0.1}
                for i, doc in enumerate(docs)
            ]
            new_state["is_relevant"] = len(docs) > 0
            return new_state
        except Exception:
            new_state = state.copy()
            new_state["retrieved_docs"] = []
            new_state["is_relevant"] = False
            return new_state


class GraderNode:
    """Evaluates relevance of retrieved documents (Self-RAG pattern)."""

    async def __call__(self, state: AgentState) -> AgentState:
        docs = state.get("retrieved_docs", [])
        if not docs:
            new_state = state.copy()
            new_state["is_relevant"] = False
            return new_state

        new_state = state.copy()
        scores = await grade_documents(state.get("_judge"), state.get("user_message", ""), docs)
        if scores is None:
            new_state["is_relevant"] = True
            return new_state

        kept = [
            {**doc, "score": score}
            for doc, score in zip(docs, scores)
            if score >= RELEVANCE_THRESHOLD
        ]
        new_state["retrieved_docs"] = kept
        new_state["is_relevant"] = len(kept) > 0
        return new_state


def load_professor_skill() -> str:
    """Helper to dynamically read promptProfessor.md from workspace/container."""
    possible_paths = [
        "/app/skills/promptProfessor.md",
        os.path.join(os.path.dirname(__file__), "..", "..", "skills", "promptProfessor.md"),
        os.path.join(os.path.dirname(__file__), "..", "skills", "promptProfessor.md"),
        "skills/promptProfessor.md"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
    return ""


class GeneratorNode:
    """Generates the final response based on retrieved academic context."""

    async def __call__(self, state: AgentState) -> AgentState:
        llm_provider = state.get("_llm_provider")
        chat_repository = state.get("_chat_repository")
        session_id = state.get("session_id")
        docs = state.get("retrieved_docs", [])
        query = state.get("user_message", "")

        # Load custom professor skill from file if available
        professor_skill = load_professor_skill()
        if professor_skill:
            system_base = (
                f"Você deve seguir a seguinte skill de comportamento ao interagir com o aluno:\n\n"
                f"{professor_skill}\n\n"
                "Além disso, lembre-se:\n"
                "- Apenas responda a perguntas que sejam a respeito de METODOLOGIA CIENTÍFICA, normas da ABNT/APA, trabalhos acadêmicos ou metodologia aplicada.\n"
                "- Se o discente informar que sua pesquisa é em uma área específica (ex: computação, usando colônia de formigas para otimização de rotas de dados), busque em seu conhecimento referências desse assunto e traga uma lista limpa de links acadêmicos úteis na norma ABNT correspondente. ATENÇÃO: NÃO resuma os artigos em hipótese alguma. Traga apenas os links e as referências completas de forma direta.\n"
                "- Se a pergunta estiver fora de escopo, recuse educadamente usando a resposta padrão: \"Olá! Como docente especializado em Metodologia Científica e normas da ABNT, meu foco é guiar você na estruturação e rigor científico do seu trabalho acadêmico. Por isso, não posso ajudar com assuntos fora desse escopo. Como posso auxiliar no planejamento ou formatação da sua pesquisa?\"\n"
                "- Sempre use formatação Markdown com emojis/ícones de forma visível e organizada no início de títulos e listas (ex: 📚 para referências, 📝 para notas, 🔬 para metodologia, 💡 para dicas, 📋 para passos).\n"
                "- Termine a resposta perguntando obrigatoriamente se o aluno tem alguma dúvida a respeito da explicação ou do texto fornecido."
            )
        else:
            # Fallback system prompt with styling directives (markdown & emojis) and professor persona
            system_base = (
                "Você é um Doutor em Metodologia Científica especializado em normas da ABNT (Prof. Metodologia ABNT). "
                "Você atua como um docente apaixonado por ensinar e tem o dom de transformar regras acadêmicas aparentemente engessadas em conceitos claros, lógicos e fáceis de aplicar. "
                "Sua missão é guiar os alunos na estruturação de seus trabalhos com rigor científico, eliminando o 'terror' das formatações.\n\n"
                "### Mapeamento de Área Científica e Referências (OBRIGATÓRIO):\n"
                "- No primeiro contato com o discente (ou caso a área de pesquisa dele ainda seja desconhecida/não mencionada nas mensagens), você DEVE perguntar de forma amigável para qual área do conhecimento (ex: Engenharia de Software, Medicina, Pedagogia, Direito, etc.) ele deseja elaborar a pesquisa científica, a fim de adaptar os exemplos práticos subsequentes ao seu domínio de estudo.\n"
                "- Se o discente informar que sua pesquisa é em uma área específica (ex: computação, usando colônia de formigas para otimização de rotas de dados), busque em seu conhecimento referências desse assunto e traga uma lista limpa de links acadêmicos úteis na norma ABNT correspondente. ATENÇÃO: NÃO resuma os artigos em hipótese alguma. Traga apenas os links e as referências completas de forma direta.\n\n"
                "### Regras de Escopo (CRÍTICO):\n"
                "- Apenas responda a perguntas que sejam a respeito de METODOLOGIA CIENTÍFICA, normas da ABNT/APA, trabalhos acadêmicos (TCC, artigos, monografias, etc.) ou metodologia científica aplicada a alguma área (como Engenharia de Software, Tecnologia, Redes, etc.).\n"
                "- Se a pergunta do usuário estiver fora desse escopo (por exemplo, pedir para programar código funcional fora de exemplo acadêmico, contar piadas, assuntos cotidianos, receitas, etc.), você DEVE recusar educadamente o atendimento com a seguinte resposta padrão:\n"
                "  \"Olá! Como docente especializado em Metodologia Científica e normas da ABNT, meu foco é guiar você na estruturação e rigor científico do seu trabalho acadêmico. Por isso, não posso ajudar com assuntos fora desse escopo. Como posso auxiliar no planejamento ou formatação da sua pesquisa?\"\n"
                "- Se a pergunta estiver no escopo, responda seguindo as diretrizes de resposta abaixo.\n\n"
                "### Diretrizes de Resposta (quando dentro do escopo):\n"
                "1. Tom de Voz e Ritmo: Amigável e descontraído, didático, claro e tecnicamente impecável. Evite jargões excessivos sem explicação prévia. **Muito Importante**: Mantenha um compasso de ensino um pouco mais lento. Não \"jogue\" ou despeje a resposta inteira de uma só vez para o discente. Explique pausadamente, dividindo tópicos complexos em partes progressivas para que ele possa assimilar sem pressa ou sobrecarga.\n"
                "2. Estrutura de Resposta:\n"
                "   - **Acolhimento**: Valide a dúvida do aluno com empatia (ex: 'Citação direta longa sempre causa confusão no início, mas vamos resolver isso rápido!').\n"
                "   - **A Teoria (O Porquê)**: Explique a lógica por trás da norma (a ABNT existe para padronizar e facilitar a leitura).\n"
                "   - **A Prática (O Como)**: Forneça exemplos claros e formatados em Markdown. Se a área do aluno já for conhecida, use contextos específicos dela para ilustrar; caso contrário, use tecnologia para ilustrar.\n"
                "   - **A Referência**: Indique a norma exata (ex: NBR 10520:2023, NBR 6023:2018).\n"
                "3. Formatação: Use Markdown e coloque emojis/ícones de forma visível e organizada no início de títulos e listas (ex: 📚 para referências, 📝 para notas, 🔬 para metodologia, 💡 para dicas, 📋 para passos).\n"
                "4. Final da Mensagem: Termine a resposta perguntando obrigatoriamente se o aluno tem alguma dúvida a respeito da explicação ou do texto fornecido."
            )

        # Dynamic feedback-based personalization instructions
        feedback_guidance = ""
        if chat_repository and session_id:
            try:
                history = await chat_repository.get_history(session_id, limit=20)
                liked = [h.content for h in history if h.feedback == "like" and h.content]
                disliked = [h.content for h in history if h.feedback == "dislike" and h.content]
                if liked or disliked:
                    feedback_guidance = "\n\n[DIRETRIZES DE PERSONALIZAÇÃO DE ACORDO COM FEEDBACK DO USUÁRIO]:\n"
                    if liked:
                        feedback_guidance += f"- Dê preferência para respostas com o mesmo tom, estilo e profundidade desta resposta que o usuário gostou: \"{liked[-1][:250]}...\"\n"
                    if disliked:
                        feedback_guidance += f"- EVITE responder do mesmo jeito ou cometer as falhas desta resposta que o usuário NÃO gostou: \"{disliked[-1][:250]}...\"\n"
            except Exception:
                pass

        system_prompt = system_base + feedback_guidance

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        if docs:
            context = "\n\n".join([d.get("content", "") for d in docs])
            messages = [
                {"role": "system", "content": (
                    f"{system_base}\n\nUse o contexto abaixo auxiliar na resposta se necessário.\n\nContexto:\n{context[:2000]}\n\n"
                    f"{feedback_guidance}"
                )},
                {"role": "user", "content": query}
            ]

        try:
            if llm_provider:
                response_parts = []
                async for chunk in llm_provider.chat(messages, max_tokens=500, temperature=0.0, stream=True):
                    response_parts.append(chunk)
                response = "".join(response_parts)
            else:
                response = f"Não encontrei referências diretas na base para a consulta: '{query}'. Por favor, reformule com termos acadêmicos ou normas específicas."
        except Exception as e:
            response = f"Não consegui gerar resposta: {str(e)}"

        new_state = state.copy()
        new_state["final_response"] = response
        return new_state


class CitationNode:
    """Standardizes retrieved sources into ABNT NBR 6023 / NBR 10520 references."""

    def _format_reference(self, doc: dict, index: int) -> str:
        meta = doc.get("metadata", {})
        title = meta.get("title") or meta.get("name") or f"Documento Científico #{index + 1}"
        author = meta.get("author") or "INSTITUTO FEDERAL DO CEARÁ (IFCE) / ABNT"
        year = meta.get("year") or meta.get("date") or "2024"
        url = meta.get("url") or meta.get("source")
        page = meta.get("page")
        section = meta.get("section")
        
        base_ref = ""
        if url:
            base_ref = f"{author}. **{title}**. {year}. Disponível em: <{url}>."
        else:
            base_ref = f"{author}. **{title}**. {year}."
            
        extras = []
        if section:
            extras.append(f"Seção: {section}")
        if page:
            extras.append(f"Página: {page}")
            
        if extras:
            return f"{base_ref} [{', '.join(extras)}]"
        return base_ref

    async def __call__(self, state: AgentState) -> AgentState:
        docs = state.get("retrieved_docs", [])
        new_state = state.copy()

        if not docs:
            new_state["abnt_references"] = []
            return new_state

        references = [self._format_reference(doc, idx) for idx, doc in enumerate(docs)]
        new_state["abnt_references"] = references

        current_response = new_state.get("final_response", "")
        if references and current_response:
            refs_formatted = "\n".join([f"- {ref}" for ref in references])
            new_state["final_response"] = f"{current_response}\n\n### 📚 Referências (ABNT NBR 6023)\n{refs_formatted}"

        return new_state


# ---------------------------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------------------------

def build_agent_graph() -> StateGraph[AgentState]:
    """Build the LangGraph state machine for the RAG agent."""

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("guardrail", GuardrailNode())
    graph.add_node("router", RouterNode())
    graph.add_node("optimizer", OptimizerNode())
    graph.add_node("retriever", RetrieverNode())
    graph.add_node("grader", GraderNode())
    graph.add_node("refusal", RefusalNode())
    graph.add_node("generator", GeneratorNode())
    graph.add_node("hallucination", HallucinationCheckerNode())
    graph.add_node("citation", CitationNode())

    # Entry point
    graph.add_edge(START, "guardrail")

    # Guardrail conditional edge
    def route_from_guardrail(state: AgentState) -> str:
        if state.get("is_injection", False):
            return "END"
        return "ROUTER"

    graph.add_conditional_edges(
        "guardrail",
        route_from_guardrail,
        {
            "END": END,
            "ROUTER": "router",
        },
    )

    # Conditional edge: router decides next step
    def route_from_router(state: AgentState) -> str:
        return state.get("_route", "RETRIEVE")

    graph.add_conditional_edges(
        "router",
        route_from_router,
        {
            "OPTIMIZE": "optimizer",
            "RETRIEVE": "retriever",
            "END": END,
        },
    )

    # optimizer always goes to retriever
    graph.add_edge("optimizer", "retriever")

    graph.add_edge("retriever", "grader")

    # grader conditional edge
    def route_from_grader(state: AgentState) -> str:
        if state.get("is_relevant", False):
            return "GENERATOR"
        return "REFUSAL"

    graph.add_conditional_edges(
        "grader",
        route_from_grader,
        {
            "GENERATOR": "generator",
            "REFUSAL": "refusal",
        },
    )

    # refusal goes to END
    graph.add_edge("refusal", END)

    # generator flows to hallucination checker
    graph.add_edge("generator", "hallucination")

    # hallucination always flows to citation node
    graph.add_edge("hallucination", "citation")

    # citation node ends the flow
    graph.add_edge("citation", END)

    return graph.compile()