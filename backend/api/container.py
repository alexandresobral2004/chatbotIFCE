"""Composition root: cria os adapters uma vez, a partir do ambiente. Único lugar que escolhe implementações."""
from functools import lru_cache

from dotenv import load_dotenv

# O .env precisa ser carregado ANTES de importar os adapters: vários leem variáveis de ambiente
# no nível do módulo (ex.: OPENAI_API_KEY). Não mova estes imports para o topo.
load_dotenv()

import os  # noqa: E402
from adapters.openai_adapter import OpenAIAdapter
from adapters.pgvector_adapter import PgVectorAdapter
from adapters.postgres_chat_adapter import PostgresChatAdapter
from adapters.postgres_usage_adapter import PostgresUsageAdapter
from adapters.postgres_user_adapter import PostgresUserAdapter
from core.application.auth_service import AuthService
from core.chat_agent import ChatAgent

database_url = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('POSTGRES_USER', 'rag_db')}:{os.getenv('POSTGRES_PASSWORD', 'rag_password')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'rag_db')}"
)

_postgres_usage_adapter = PostgresUsageAdapter(database_url)

llm_provider_name = os.getenv("LLM_PROVIDER", "openai").lower()

if llm_provider_name == "deepseek":
    from adapters.deepseek_adapter import DeepSeekAdapter
    _llm_provider = DeepSeekAdapter(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        usage_adapter=_postgres_usage_adapter,
    )
elif llm_provider_name == "groq":
    from adapters.groq_adapter import GroqAdapter
    _llm_provider = GroqAdapter(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL", "groq/compound"),
        usage_adapter=_postgres_usage_adapter,
    )
else:
    _llm_provider = OpenAIAdapter(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        usage_adapter=_postgres_usage_adapter,
    )

_validator_llm = OpenAIAdapter(
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("VALIDATOR_MODEL", "gpt-5.6-luna"),
    embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    usage_adapter=_postgres_usage_adapter,
)

_vector_repository = PgVectorAdapter(
    connection_string=database_url,
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    embedding_dim=int(os.getenv("OPENAI_EMBEDDING_DIM", "1536")),
)

_postgres_chat_adapter = PostgresChatAdapter(database_url)

_user_adapter = PostgresUserAdapter(database_url)
_auth_service = AuthService(_user_adapter)


@lru_cache(maxsize=1)
def get_typesafe_adapter():
    """Adapter do Jev (implementa JudgePort). Criado uma vez, sob demanda (o SDK só carrega se usado)."""
    from adapters.typesafe_adapter import TypeSafeAdapter
    return TypeSafeAdapter()


def get_chat_agent() -> ChatAgent:
    return ChatAgent(
        vector_repository=_vector_repository,
        chat_repository=_postgres_chat_adapter,
        llm_provider=_llm_provider,
        validator_llm=_validator_llm,
        judge=get_typesafe_adapter(),
    )


@lru_cache(maxsize=1)
def get_project_knowledge_service():
    """Serviço de perguntas sobre o projeto, criado uma vez, sob demanda."""
    from core.application.project_knowledge import ProjectKnowledgeService
    return ProjectKnowledgeService(get_typesafe_adapter())
