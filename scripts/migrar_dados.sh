#!/bin/bash
# Copia a base de conhecimento (RAG) e o histórico do chat do Postgres ANTIGO para o NOVO.
# Só LÊ do banco de origem (pg_dump) e só ESCREVE no banco de destino. Não apaga nada na origem.
#
# Uso:
#   SOURCE_DATABASE_URL=postgresql://... TARGET_DATABASE_URL=postgresql://... ./scripts/migrar_dados.sh
#
# Pré-requisitos: psql e pg_dump instalados; o destino já com o schema (backend/migrations/001_init.sql).
# Idempotente na prática: se o destino já tem dados nas tabelas copiadas, o script aborta (use um banco vazio).
set -euo pipefail

: "${SOURCE_DATABASE_URL:?defina SOURCE_DATABASE_URL}"
: "${TARGET_DATABASE_URL:?defina TARGET_DATABASE_URL}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
TABLES=(knowledge_documents document_chunks chat_sessions chat_messages)
DUMP="$(mktemp -t chat_dump.XXXXXX)"
trap 'rm -f "$DUMP"' EXIT

echo "== 1/4 Aplicando o schema no destino"
psql "$TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 -q -f "$HERE/backend/migrations/001_init.sql"

echo "== 2/4 Conferindo que o destino está vazio"
for t in "${TABLES[@]}"; do
  n=$(psql "$TARGET_DATABASE_URL" -tAc "SELECT count(*) FROM $t")
  [ "$n" = "0" ] || { echo "ERRO: $t no destino já tem $n linhas. Use um banco vazio."; exit 1; }
done

echo "== 3/4 Exportando da origem (somente leitura) e importando no destino"
args=(); for t in "${TABLES[@]}"; do args+=(-t "$t"); done
pg_dump "$SOURCE_DATABASE_URL" --data-only --no-owner --no-privileges "${args[@]}" > "$DUMP"
# Em uma transação: ou entra tudo, ou nada.
psql "$TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 -q --single-transaction -f "$DUMP"

echo "== 4/4 Conferindo contagens (origem x destino)"
ok=1
for t in "${TABLES[@]}"; do
  a=$(psql "$SOURCE_DATABASE_URL" -tAc "SELECT count(*) FROM $t")
  b=$(psql "$TARGET_DATABASE_URL" -tAc "SELECT count(*) FROM $t")
  printf '%-22s origem=%s destino=%s\n' "$t" "$a" "$b"
  [ "$a" = "$b" ] || ok=0
done
[ "$ok" = "1" ] && echo "OK: migração conferida." || { echo "ATENÇÃO: contagens diferentes."; exit 1; }
