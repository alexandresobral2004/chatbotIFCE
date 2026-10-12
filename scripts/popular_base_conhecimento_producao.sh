#!/bin/bash
# Popula a base de conhecimento (RAG) do JupiterClass em PRODUÇÃO (Railway).
#
# O que faz, em ordem:
#   1. Cria as tabelas que faltam no Postgres de produção (knowledge_documents,
#      document_chunks, chat_sessions, chat_messages) — idempotente, seguro
#      rodar mais de uma vez (CREATE TABLE IF NOT EXISTS).
#   2. Envia os PDFs novos de documents/ para o container do backend.
#   3. Roda a ingestão (extrai texto -> gera embeddings OpenAI -> grava no
#      pgvector) para o manual do IFCE + os 4 documentos novos.
#
# Pré-requisitos: `railway` CLI instalado e logado (`railway whoami`), e este
# diretório já vinculado ao projeto JupiterClass (`railway status`).
#
# Uso:
#   chmod +x scripts/popular_base_conhecimento_producao.sh
#   ./scripts/popular_base_conhecimento_producao.sh

set -e

cd "$(dirname "$0")/.."

echo "=== 0. Verificando link com o Railway ==="
railway status

echo ""
echo "=== 1. Criando tabelas faltantes no Postgres de produção ==="
cat <<'PYEOF' | railway ssh --service backend -- /usr/local/bin/python3.11 -
import asyncio, asyncpg, os

SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID REFERENCES knowledge_documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_streaming BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'idle',
    context_loaded BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);
CREATE INDEX IF NOT EXISTS idx_chat_messages_timestamp ON chat_messages(timestamp);
"""

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute(SQL)
    print("Migração aplicada com sucesso.")
    for t in ["knowledge_documents", "document_chunks", "chat_sessions", "chat_messages"]:
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = $1)", t
        )
        print(f"  {t}: {'OK' if exists else 'FALTANDO'}")
    await conn.close()

asyncio.run(main())
PYEOF

# Envia um PDF local e roda a ingestão. IMPORTANTE: usa `tee` com o comando
# remoto direto (sem "bash -c '...&&...'"), porque encadear comandos dentro
# de uma string bash -c pelo "railway ssh --" corrompe silenciosamente flags
# como "base64 -d" (o -d some e o arquivo remoto fica com o conteúdo
# re-codificado em vez de decodificado). "railway service files upload"
# também não é confiável aqui — grava num container diferente do que o ssh
# acessa depois. `tee` puro em texto claro (sem base64) é binário-seguro via
# stdin do SSH e funciona de forma consistente.
ingest_local_pdf() {
    local local_path="$1"
    local remote_name="$2"
    echo "--- Enviando: $remote_name ---"
    cat "$local_path" | railway ssh --service backend -- tee "/app/$remote_name" > /dev/null
    echo "--- Ingerindo: $remote_name ---"
    railway ssh --service backend -- /usr/local/bin/python3.11 ingest/ingest_pdf.py "$remote_name"
}

echo ""
echo "=== 2. Ingerindo documentos (envio + extração + embeddings OpenAI + pgvector) ==="
echo "--- Manual de Normalização do IFCE (já está na imagem) ---"
railway ssh --service backend -- /usr/local/bin/python3.11 ingest/ingest_pdf.py ingest/manual_ifce_2020.pdf

ingest_local_pdf "backend/knowledge/Metodologia-de-Pesquisa-para-Ciência-da-Computação-3_21-Raul-Sidnei-Wazlawick-3_-2021-GEN-LTC-978859.pdf" "livro_wazlawick_metodologia_pesquisa_cc.pdf"
ingest_local_pdf "backend/knowledge/Resolucao_CNS_466_2012_Etica_Pesquisa.pdf" "Resolucao_CNS_466_2012_Etica_Pesquisa.pdf"
ingest_local_pdf "backend/knowledge/Resolucao_CNS_510_2016_Etica_CHSA.pdf" "Resolucao_CNS_510_2016_Etica_CHSA.pdf"
ingest_local_pdf "backend/knowledge/Tabela_Areas_Conhecimento_CNPq.pdf" "Tabela_Areas_Conhecimento_CNPq.pdf"

echo ""
echo "=== Concluído! Verificando total de chunks indexados ==="
cat <<'PYEOF' | railway ssh --service backend -- /usr/local/bin/python3.11 -
import asyncio, asyncpg, os

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    total = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")
    docs = await conn.fetch("SELECT title FROM knowledge_documents ORDER BY created_at")
    print(f"Total de chunks indexados: {total}")
    print("Documentos na base:")
    for d in docs:
        print(f"  - {d['title']}")
    await conn.close()

asyncio.run(main())
PYEOF
