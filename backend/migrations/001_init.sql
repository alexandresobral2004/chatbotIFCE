-- Schema do chat (banco próprio do serviço). Idempotente. Extraído de init.sql do sistema original.
-- Create extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Knowledge documents table
CREATE TABLE IF NOT EXISTS knowledge_documents (
    doc_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Document chunks table (stores vector embeddings)
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID REFERENCES knowledge_documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions table (user conversations)
CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages table (the main conversation history)
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

-- Index for efficient vector search (HNSW algorithm)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);

-- Colunas adicionadas depois do init.sql original (já existem em produção)
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS processing_time_ms INTEGER;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS rag_version VARCHAR(50);
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS model_version VARCHAR(100);
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS feedback VARCHAR(10);

-- Usuários do chat (login e cadastro próprios)
CREATE TABLE IF NOT EXISTS chat_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
