"""ingest_markdown.py — Carrega guias Markdown no banco pgvector.

Uso:
    python ingest_markdown.py /caminho/para/guia.md [--source-url URL]

Fluxo:
    1. Extract  — lê o arquivo .md
    2. Transform — RecursiveCharacterTextSplitter divide em chunks
    3. Generate — OpenAIEmbeddings gera vetores 1536d
    4. Load     — Insere knowledge_documents + document_chunks no PostgreSQL
"""

import argparse
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

import psycopg2
import psycopg2.extras
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingest_markdown")

from dotenv import load_dotenv
load_dotenv()
load_dotenv(dotenv_path="../.env")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("OPENAI_EMBEDDING_DIM", "1536"))

DB_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST", "127.0.0.1")
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


def extract_markdown(md_path: str) -> tuple[str, str]:
    """Lê o arquivo Markdown e retorna título + conteúdo bruto."""
    logger.info("📄 Extracting Markdown: %s", md_path)
    if not os.path.isfile(md_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {md_path}")

    title = os.path.splitext(os.path.basename(md_path))[0]
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    logger.info("  → Título: %s", title)
    logger.info("  → Tamanho: %d caracteres", len(content))
    return title, content


def transform_content(content: str, title: str) -> List[ChunkResult]:
    """Divide o conteúdo em chunks."""
    logger.info("✂️  Transforming content into chunks…")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=False,
    )

    split_docs = splitter.split_text(content)

    chunks: List[ChunkResult] = []
    for doc in split_docs:
        chunks.append(
            ChunkResult(
                content=doc,
                metadata={
                    "source": title,
                    "document_title": title,
                    "type": "markdown",
                },
            )
        )

    logger.info("  → Chunks gerados: %d", len(chunks))
    return chunks


def generate_embeddings(chunks: List[ChunkResult]) -> List[List[float]]:
    """Gera embeddings para todos os chunks usando OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY")

    logger.info(
        "🧠 Generating embeddings com modelo %s (%dd) via OpenAI…",
        EMBEDDING_MODEL,
        EMBEDDING_DIM,
    )

    if not api_key:
        raise EnvironmentError(
            "Nenhuma chave de API (OPENAI_API_KEY) foi encontrada."
        )

    embeddings_provider = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_key=api_key,
        max_retries=3,
    )

    texts = [chunk.content for chunk in chunks]
    embedding_vectors = embeddings_provider.embed_documents(texts)

    logger.info("  → VETORES gerados: %d (dimensão %d)", len(embedding_vectors), EMBEDDING_DIM)
    return embedding_vectors


def load_to_postgres(
    title: str,
    source_url: str,
    chunks: List[ChunkResult],
    embedding_vectors: List[List[float]],
    dry_run: bool = False,
) -> None:
    """Insere documento + chunks no PostgreSQL com transação ACID."""
    logger.info("🗄️  Loading data no PostgreSQL…")

    conn = None
    start_time = time.time()

    try:
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
        logger.info("  → doc_id: %s", doc_id)

        if dry_run:
            logger.info("  [DRY-RUN] Insert em knowledge_documents: SKIP")
            logger.info("  [DRY-RUN] Insert em document_chunks: %d chunks → SKIP", len(chunks))
            return

        insert_doc_sql = f"""
            INSERT INTO {DB_TABLE_DOCUMENTS} (doc_id, title, source_url)
            VALUES (%s, %s, %s)
            RETURNING doc_id
        """
        cursor.execute(insert_doc_sql, (doc_id, title, source_url))
        row = cursor.fetchone()
        logger.info("  → knowledge_documents inserido: %s", row[0] if row else doc_id)

        insert_chunk_sql = f"""
            INSERT INTO {DB_TABLE_CHUNKS} (chunk_id, doc_id, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """
        chunk_records = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embedding_vectors)):
            chunk_id = str(uuid.uuid4())
            chunk_records.append((
                chunk_id,
                doc_id,
                chunk.content,
                vector,
                psycopg2.extras.Json(chunk.metadata),
            ))
            if (idx + 1) % 100 == 0 or (idx + 1) == len(chunks):
                logger.info("  → Chunks preparados: %d / %d", idx + 1, len(chunks))

        psycopg2.extras.execute_batch(
            cursor,
            insert_chunk_sql,
            chunk_records,
            page_size=50,
        )
        logger.info("  → document_chunks inseridos: %d", len(chunk_records))

        conn.commit()
        elapsed = time.time() - start_time
        logger.info("  ✅ COMMIT realizado com sucesso em %.2fs", elapsed)

    except psycopg2.Error as db_err:
        if conn:
            conn.rollback()
        logger.error("  ❌ Erro no banco de dados → ROLLBACK")
        logger.error("  → Detalhes: %s", db_err)
        raise RuntimeError(f"Falha na inserção PostgreSQL: {db_err}") from db_err

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("  ❌ Erro inesperado → ROLLBACK")
        logger.error("  → Detalhes: %s", e)
        raise RuntimeError(f"Falha no processamento: {e}") from e

    finally:
        if conn:
            conn.close()
            logger.debug("  → Conexão PostgreSQL fechada")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingestão de guias Markdown para pgvector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "md_path",
        type=str,
        help="Caminho para o arquivo Markdown",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default="",
        help="URL de origem do guia (opcional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sem inserir no banco",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("🚀 Ingestão iniciada para: %s", args.md_path)
    logger.info("=" * 60)

    try:
        title, content = extract_markdown(args.md_path)
        chunks = transform_content(content, title)

        if not chunks:
            logger.warning("⚠️  Nenhum chunk gerado. Verifique o arquivo.")
            sys.exit(1)

        embedding_vectors = generate_embeddings(chunks)
        source_url = args.source_url or f"file://{os.path.abspath(args.md_path)}"
        load_to_postgres(title, source_url, chunks, embedding_vectors, dry_run=args.dry_run)

        logger.info("=" * 60)
        logger.info("✅ Ingestão concluída com sucesso!")
        logger.info("=" * 60)

    except FileNotFoundError as fnf_err:
        logger.error("❌ %s", fnf_err)
        sys.exit(1)
    except EnvironmentError as env_err:
        logger.error("❌ %s", env_err)
        sys.exit(1)
    except Exception as e:
        logger.error("❌ Falha fatal: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()