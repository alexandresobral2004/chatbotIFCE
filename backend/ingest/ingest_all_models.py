"""ingest_all_models.py — Ingestão de todos os modelos DOCX e ODT do IFCE no pgvector."""

import os
import sys
import uuid
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

HERE = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest_all_models")

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

def extract_file(file_path: str) -> tuple[str, str]:
    title = os.path.splitext(os.path.basename(file_path))[0]
    ext = os.path.splitext(file_path)[1].lower()
    paragraphs = []

    if ext == ".docx":
        logger.info("📄 Lendo DOCX: %s", file_path)
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                texts = [node.text for node in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
                if texts:
                    paragraphs.append("".join(texts))
    elif ext == ".odt":
        logger.info("📄 Lendo ODT: %s", file_path)
        with zipfile.ZipFile(file_path) as z:
            xml_content = z.read("content.xml")
            tree = ET.fromstring(xml_content)
            for p in tree.iter("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p"):
                t = "".join([node.text for node in p.iter() if node.text])
                if t.strip():
                    paragraphs.append(t)
    else:
        raise ValueError(f"Extensão não suportada: {ext}")

    full_text = "\n\n".join(paragraphs)
    return title, full_text

def transform_text(text: str, title: str, source_url: str) -> List[ChunkResult]:
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
                    "source_url": source_url,
                    "type": "template_ifce"
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
    logger.info("✅ %s: %d chunks inseridos com sucesso no PostgreSQL!", title, len(records))

def process_file(file_path: str, url: str):
    if not os.path.exists(file_path):
        logger.error("❌ Arquivo não encontrado: %s", file_path)
        return
    title, text = extract_file(file_path)
    chunks = transform_text(text, title, url)
    logger.info("✂️ %s: %d chunks gerados", title, len(chunks))
    vectors = generate_embeddings(chunks)
    load_to_postgres(title, url, chunks, vectors)

if __name__ == "__main__":
    templates = [
        (os.path.join(HERE, "modelo_artigo_ifce.docx"), "https://portal.ifce.edu.br/documents/3282/Modelo_de_artigo_cient%C3%ADfico_em_Microsoft_Word.docx"),
        (os.path.join(HERE, "modelo_trabalho_ifce.odt"), "https://portal.ifce.edu.br/documents/3283/Modelo_de_trabalho_acad%C3%AAmico_em_LibreOffice.odt"),
        (os.path.join(HERE, "modelo_artigo_ifce.odt"), "https://portal.ifce.edu.br/documents/3281/Modelo_de_artigo_cient%C3%ADfico_em_LibreOffice.odt")
    ]
    for path, url in templates:
        process_file(path, url)
    logger.info("🎉 Todos os modelos e templates foram ingeridos com sucesso!")
