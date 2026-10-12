"""Rede de segurança da extração do chatbot para um projeto próprio (Fase 0 do desmembramento).

1. O contrato SSE do chat (formato dos eventos de `stream_events`) não pode mudar: o frontend e o futuro serviço dependem dele.
2. A fatia do chat no core só pode depender de si mesma e de portas, para poder ser copiada sem arrastar o resto do sistema.
"""
import ast
import asyncio
from pathlib import Path

from core.chat_agent import ChatAgent

BACKEND = Path(__file__).resolve().parent.parent

# Arquivos que vão para o novo projeto (lado do core).
CHAT_CORE = {
    "core/chat_agent.py",
    "core/langgraph_flow.py",
    "core/state.py",
    "core/prompts.py",
    "core/application/jev_judgments.py",
    "core/application/project_knowledge.py",
}
# Módulos locais que a fatia do chat pode importar (portas e domínio); o resto do sistema é proibido.
ALLOWED_LOCAL = {"ports", "core"}
ALLOWED_CORE_MODULES = {
    "core.chat_agent", "core.langgraph_flow", "core.state", "core.prompts", "core.domain",
    "core.application.jev_judgments", "core.application.project_knowledge",
}


class _FakeChatRepo:
    def __init__(self):
        self.saved = []

    async def save_message(self, **kwargs):
        self.saved.append(kwargs)


class _FakeGraph:
    def __init__(self, result=None, error=None):
        self._result, self._error = result, error

    async def ainvoke(self, state):
        if self._error:
            raise self._error
        return self._result


def _agent(graph):
    agent = ChatAgent(vector_repository=object(), chat_repository=_FakeChatRepo(), llm_provider=object())
    agent._graph = graph
    return agent


def _collect(agent):
    async def run():
        return [e async for e in agent.stream_events("sid", "oi")]
    return asyncio.run(run())


def test_sse_contract_status_then_tokens_then_history_saved():
    agent = _agent(_FakeGraph({"final_response": "a" * 45}))
    events = _collect(agent)

    assert events[0] == {"type": "status", "status": "Gerando resposta...", "node": "generator"}
    tokens = [e for e in events[1:] if e["type"] == "token"]
    assert [set(t) for t in tokens] == [{"type", "content"}] * 3
    assert "".join(t["content"] for t in tokens) == "a" * 45
    assert [m["role"] for m in agent._chat_repository.saved] == ["user", "assistant"]
    assert {"processing_time_ms", "rag_version", "model_version"} <= set(agent._chat_repository.saved[1])


def test_sse_contract_error_event_shape():
    events = _collect(_agent(_FakeGraph(error=RuntimeError("falhou"))))
    assert events == [{"type": "error", "error": "falhou"}]


def _local_imports(path: Path):
    pkg = path.relative_to(BACKEND).with_suffix("").parts[:-1]
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = list(pkg[: len(pkg) - (node.level - 1)])
                yield ".".join(base + ([node.module] if node.module else [])), [a.name for a in node.names]
            elif node.module:
                yield node.module, [a.name for a in node.names]


def test_chat_core_slice_depends_only_on_ports_and_itself():
    offenders = []
    for rel in sorted(CHAT_CORE):
        for module, names in _local_imports(BACKEND / rel):
            top = module.split(".")[0]
            if top not in ALLOWED_LOCAL:
                continue
            if top == "core":
                # `from . import x` / `from .. import x` aparece como o pacote; confere cada nome importado.
                targets = [module] if (BACKEND / (module.replace(".", "/") + ".py")).exists() else [f"{module}.{n}" for n in names]
                if not all(any(t == a or t.startswith(a + ".") for a in ALLOWED_CORE_MODULES) for t in targets):
                    offenders.append(f"{rel} importa {module} ({', '.join(names)})")
    assert not offenders, "a fatia do chat depende do resto do sistema:\n  " + "\n  ".join(offenders)
