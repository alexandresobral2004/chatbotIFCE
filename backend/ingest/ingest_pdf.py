"""ingest_pdf.py — Carrega artigos científicos PDFs no banco pgvector.

Uso:
    python ingest_pdf.py /caminho/para/artigo.pdf [--dry-run] [--verbose]

Fluxo:
    1. Extract  — PyPDFLoader lê o PDF
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
from langchain_community.document_loaders import PyPDFLoader
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
logger = logging.getLogger("ingest_pdf")

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

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ChunkResult:
    content: str
    metadata: dict
    page_number: int

# ---------------------------------------------------------------------------
# Step 1 — Extract
# ---------------------------------------------------------------------------
def extract_pdf(pdf_path: str) -> tuple[str, List]:
    """Carrega o PDF e retorna o título + documentos brutos."""
    logger.info("📄 Extracting PDF: %s", pdf_path)
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"Arquivo não encontrado: {pdf_path}")

    title = os.path.splitext(os.path.basename(pdf_path))[0]
    loader = PyPDFLoader(file_path=pdf_path)
    documents = loader.load()

    logger.info("  → Título: %s", title)
    logger.info("  → Páginas carregadas: %d", len(documents))
    return title, documents

# ---------------------------------------------------------------------------
# Step 2 — Transform
# ---------------------------------------------------------------------------
def transform_documents(documents: List, title: str) -> List[ChunkResult]:
    """Divide os documentos em chunks mantendo metadados de página."""
    logger.info("✂️  Transforming documents into chunks…")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=False,
    )

    # LangChain splits and attaches page metadata automatically
    split_docs = splitter.split_documents(documents)

    chunks: List[ChunkResult] = []
    for doc in split_docs:
        page_number = doc.metadata.get("page", 0)
        chunks.append(
            ChunkResult(
                content=doc.page_content,
                metadata={
                    "source": title,
                    "page": page_number,
                    "document_title": title,
                },
                page_number=page_number,
            )
        )

    logger.info("  → Chunks gerados: %d", len(chunks))
    return chunks

# ---------------------------------------------------------------------------
# Step 3 — Generate Embeddings
# ---------------------------------------------------------------------------
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
    embedding_vectors: List[List[float]] = []
    batch_size = 40
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        logger.info("  → Gerando embeddings lote %d / %d", (i // batch_size) + 1, (len(texts) + batch_size - 1) // batch_size)
        batch_vectors = embeddings_provider.embed_documents(batch)
        embedding_vectors.extend(batch_vectors)

    logger.info("  → VETORES gerados: %d (dimensão %d)", len(embedding_vectors), EMBEDDING_DIM)
    return embedding_vectors

# ---------------------------------------------------------------------------
# Step 4 — Load (PostgreSQL)
# ---------------------------------------------------------------------------
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
        conn.autocommit = False  # transação manual
        cursor = conn.cursor()

        doc_id = str(uuid.uuid4())
        logger.info("  → doc_id: %s", doc_id)

        if dry_run:
            logger.info("  [DRY-RUN] Insert em knowledge_documents: SKIP")
            logger.info("  [DRY-RUN] Insert em document_chunks: %d chunks → SKIP", len(chunks))
            logger.info("  [DRY-RUN] → ROLLBACK (simulação)")
            return

        # --- Insert knowledge_documents ---
        insert_doc_sql = f"""
            INSERT INTO {DB_TABLE_DOCUMENTS} (doc_id, title, source_url)
            VALUES (%s, %s, %s)
            RETURNING doc_id
        """
        cursor.execute(insert_doc_sql, (doc_id, title, source_url))
        row = cursor.fetchone()
        logger.info("  → knowledge_documents inserido: %s", row[0] if row else doc_id)

        # --- Batch insert document_chunks ---
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

        # Execute em lote
        psycopg2.extras.execute_batch(
            cursor,
            insert_chunk_sql,
            chunk_records,
            page_size=50,
        )
        logger.info("  → document_chunks inseridos: %d", len(chunk_records))

        # Commit
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

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingestão de artigos científicos PDF para pgvector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python ingest_pdf.py ./artigos/meu_artigo.pdf
  python ingest_pdf.py ./artigos/meu_artigo.pdf --dry-run --verbose
        """,
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Caminho para o arquivo PDF",
    )
    parser.add_argument(
        "--source-url",
        type=str,
        default="",
        help="URL de origem do artigo (opcional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sem inserir no banco",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log detalhado",
    )
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("🚀 Ingestão iniciada para: %s", args.pdf_path)
    logger.info("=" * 60)

    try:
        # 1. Extract
        title, documents = extract_pdf(args.pdf_path)

        # 2. Transform
        chunks = transform_documents(documents, title)

        if not chunks:
            logger.warning("⚠️  Nenhum chunk gerado. Verifique o PDF.")
            sys.exit(1)

        # 3. Generate Embeddings
        embedding_vectors = generate_embeddings(chunks)

        # 4. Load
        source_url = args.source_url or f"file://{os.path.abspath(args.pdf_path)}"
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