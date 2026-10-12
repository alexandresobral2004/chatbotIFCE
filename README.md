# jupiterclass-chat

Chatbot RAG de metodologia científica, extraído do sistema JupiterClass como serviço independente.

- `backend/`: FastAPI + LangGraph + pgvector; Jev (TypeSafe) para os julgamentos. Arquitetura hexagonal (`core/` → `ports/` ← `adapters/`).
- `frontend/`: Next.js com a tela de login/cadastro e o `ChatInterface`; serve também como widget para iframe.

## Rodar local
```bash
docker compose up db -d                # Postgres + pgvector (aplica backend/migrations)
cd backend && python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env                   # preencher chaves
.venv/bin/uvicorn main:app --reload
cd ../frontend && npm install && npm run dev   # http://localhost:3001
.venv/bin/python -m pytest             # (em backend/)
```

## Autenticação
- Cadastro e login próprios: `POST /api/auth/register`, `POST /api/auth/login` (devolvem um JWT HS256), `GET /api/auth/me`.
- `/chat/*` e `/api/project/ask` exigem `Authorization: Bearer <jwt>` (`CHAT_AUTH_REQUIRED=false` só em dev).
- O widget também aceita um token emitido pelo sistema principal (mesmo `CHAT_JWT_SECRET`), via `#token=` na URL ou `postMessage`.

## Base de conhecimento
`backend/ingest/` (scripts) e `backend/knowledge/` (PDFs). Produção: `scripts/popular_base_conhecimento_producao.sh` (não validado após a extração).
`backend/core/project_knowledge.json` é um retrato estático do sistema original; o gerador não veio junto.

## Migração de dados
`scripts/migrar_dados.sh` copia a base de conhecimento e o histórico do Postgres antigo para o novo (somente leitura na origem; destino vazio; conferência de contagens). **Ainda não foi executado.**
As conversas antigas ficam sem dono (`user_id` nulo: o sistema original nunca o gravava), então não aparecem para nenhum usuário pela API; servem só como arquivo.

## Origem
Extraído de `chatbot` (commit fbe40d5). Os arquivos foram copiados sem o histórico git.
