#!/bin/bash
set -e

echo "=== JupiterClass Chat: Iniciando ==="
echo "PORT=$PORT"

echo "=== Aguardando banco de dados ==="
python -c "
import os, time, psycopg2
db = os.environ['DATABASE_URL']
for i in range(30):
    try:
        psycopg2.connect(db).close()
        print('DB pronto!')
        break
    except Exception as e:
        print(f'Tentativa {i+1}/30: {e}')
        time.sleep(2)
"

echo "=== Aplicando migrations (idempotentes) ==="
python -c "
import glob, os, psycopg2
conn = psycopg2.connect(os.environ['DATABASE_URL'])
conn.autocommit = True
for f in sorted(glob.glob('migrations/*.sql')):
    print('Aplicando', f)
    conn.cursor().execute(open(f, encoding='utf-8').read())
conn.close()
"

echo "=== Iniciando servidor FastAPI ==="
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
