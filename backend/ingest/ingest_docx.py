"""ingest_docx.py — Ingestão de templates e documentos DOCX no banco pgvector."""

import os
import sys
import uuid
import time
import zipfile
import logging
import xml.etree.ElementTree as ET
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
logger = logging.getLogger("ingest_docx")

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

def extract_docx(docx_path: str) -> tuple[str, str]:
    logger.info("📄 Extracting DOCX: %s", docx_path)
    title = os.path.splitext(os.path.basename(docx_path))[0]
    
    with zipfile.ZipFile(docx_path) as z:
        xml_content = z.read("word/document.xml")
        tree = ET.fromstring(xml_content)
        paragraphs = []
        for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
            texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
            if texts:
                paragraphs.append("".join(texts))
        
        full_text = "\n\n".join(paragraphs)
        return title, full_text

def transform_text(text: str, title: str) -> List[ChunkResult]:
    logger.info("✂️ Transforming text into chunks…")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    docs = splitter.split_text(text)
    chunks = []
    for doc in docs:
        chunks.append(
            ChunkResult(
                content=doc,
                metadata={
                    "source": title,
                    "document_title": title,
                    "type": "template_docx"
                }
            )
        )
    logger.info("  → Chunks gerados: %d", len(chunks))
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

def load_to_postgres(title: str, source_url: str, chunks: List[ChunkResult], embedding_vectors: List[List[float]]) -> None:
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
    cursor.execute(insert_doc_sql, (doc_id, title, source_url))

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
    logger.info("✅ %d chunks do DOCX inseridos com sucesso!", len(records))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python ingest_docx.py arquivo.docx [source_url]")
        sys.exit(1)
    docx_file = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else f"file://{os.path.abspath(docx_file)}"
    title, text = extract_docx(docx_file)
    chunks = transform_text(text, title)
    vectors = generate_embeddings(chunks)
    load_to_postgres(title, url, chunks, vectors)
