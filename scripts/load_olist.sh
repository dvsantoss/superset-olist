#!/usr/bin/env bash
# Carrega os CSVs da Olist no banco "examples" do Postgres do Superset
# Uso: ./scripts/load_olist.sh <pasta-com-os-csvs>
set -euo pipefail

CSV_DIR="${1:?Informe a pasta com os CSVs da Olist}"
SQL_DIR="$(cd "$(dirname "$0")/../sql" && pwd)"
DB_CONTAINER="${DB_CONTAINER:-superset_db}"

run_psql() {
    docker exec -i "$DB_CONTAINER" psql -v ON_ERROR_STOP=1 -q -U examples -d examples "$@"
}

run_psql < "$SQL_DIR/01_create_tables.sql"

# Ordem importa por causa das chaves estrangeiras
for table in customers products orders order_items; do
    echo "Carregando $table..."
    run_psql -c "\copy $table FROM STDIN WITH (FORMAT csv, HEADER true)" < "$CSV_DIR/olist_${table}_dataset.csv"
done

run_psql < "$SQL_DIR/02_create_view.sql"

run_psql -c "SELECT COUNT(*) AS itens, COUNT(DISTINCT pedido_id) AS pedidos FROM vendas;"
