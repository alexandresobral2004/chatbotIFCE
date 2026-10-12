"""ingest_latex.py — Ingestão do template LaTeX oficial do IFCE (IFCETeX2 / Overleaf) no pgvector."""

import os
import sys
import uuid
import logging
from dataclasses import dataclass
from typing import List

import psycopg2
import psycopg2.extras
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest_latex")

load_dotenv()
load_dotenv(dotenv_path="../.env")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("OPENAI_EMBEDDING_DIM", "1536"))

DB_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME", "rag_db")
DB_USER = os.getenv("POSTGRES_USER") or os.getenv("DB_USER", "rag_db")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD", "rag_password")
DB_TABLE_DOCUMENTS = "knowledge_documents"
DB_TABLE_CHUNKS = "document_chunks"

@dataclass
class ChunkResult:
    content: str
    metadata: dict

def extract_tex_directory(dir_path: str) -> List[tuple[str, str]]:
    results = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith(('.tex', '.sty', '.bib')):
                full_p = os.path.join(root, f)
                rel_p = os.path.relpath(full_p, dir_path)
                try:
                    with open(full_p, 'r', encoding='utf-8', errors='ignore') as fp:
                        content = fp.read()
                        if content.strip():
                            results.append((rel_p, content))
                except Exception as e:
                    logger.warning("Falha ao ler %s: %s", full_p, e)
    return results

def transform_texts(files: List[tuple[str, str]], source_url: str) -> List[ChunkResult]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "%", "\\section", "\\chapter", " ", ""],
    )
    chunks = []
    for filename, content in files:
        sub_chunks = splitter.split_text(content)
        for c in sub_chunks:
            chunks.append(
                ChunkResult(
                    content=f"Arquivo: {filename}\n\n{c}",
                    metadata={
                        "source": "IFCETeX2_LaTeX_Template",
                        "document_title": f"IFCETeX2: {filename}",
                        "file_name": filename,
                        "source_url": source_url,
                        "type": "template_latex"
                    }
                )
            )
    return chunks

def generate_embeddings(chunks: List[ChunkResult]) -> List[List[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("Nenhuma chave de API (OPENAI_API_KEY) encontrada.")

    embeddings_provider = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=api_key,
        max_retries=3,
    )
    texts = [chunk.content for chunk in chunks]
    embedding_vectors = []
    batch_size = 40
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info("  → Gerando embeddings lote %d / %d", (i // batch_size) + 1, (len(texts) + batch_size - 1) // batch_size)
        embedding_vectors.extend(embeddings_provider.embed_documents(batch))
    return embedding_vectors

def load_to_postgres(source_url: str, chunks: List[ChunkResult], embedding_vectors: List[List[float]]) -> None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(dsn=database_url, options="-c search_path=public")
    else:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            options="-c search_path=public",
        )
    conn.autocommit = False
    cursor = conn.cursor()
    doc_id = str(uuid.uuid4())

    insert_doc_sql = f"""
        INSERT INTO {DB_TABLE_DOCUMENTS} (doc_id, title, source_url)
        VALUES (%s, %s, %s)
    """
    cursor.execute(insert_doc_sql, (doc_id, "IFCETeX2_Modelo_LaTeX_Overleaf", source_url))

    insert_chunk_sql = f"""
        INSERT INTO {DB_TABLE_CHUNKS} (chunk_id, doc_id, content, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s)
    """
    records = []
    for chunk, vector in zip(chunks, embedding_vectors):
        records.append((
            str(uuid.uuid4()),
            doc_id,
            chunk.content,
            vector,
            psycopg2.extras.Json(chunk.metadata),
        ))

    psycopg2.extras.execute_batch(cursor, insert_chunk_sql, records, page_size=50)
    conn.commit()
    conn.close()
    logger.info("✅ IFCETeX2: %d chunks de LaTeX inseridos com sucesso!", len(records))

if __name__ == "__main__":
    dir_to_read = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ifcetex2")
    overleaf_url = "https://www.overleaf.com/read/pzrvwbmzjmzj"
    logger.info("🚀 Processando template LaTeX do diretório: %s", dir_to_read)
    files = extract_tex_directory(dir_to_read)
    logger.info("  → Total de arquivos LaTeX lidos: %d", len(files))
    chunks = transform_texts(files, overleaf_url)
    logger.info("  → Chunks gerados: %d", len(chunks))
    vectors = generate_embeddings(chunks)
    load_to_postgres(overleaf_url, chunks, vectors)
    logger.info("🎉 Ingestão do template LaTeX concluída com sucesso!")
