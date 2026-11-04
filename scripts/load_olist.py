import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql


PROJECT_DIR = Path(__file__).resolve().parent.parent
TABLES = ("customers", "products", "orders", "order_items")
BLOCK_SIZE = 1024 * 1024


def load_data(csv_dir: Path) -> tuple[int, int]:
    csv_paths = {
        table: csv_dir / f"olist_{table}_dataset.csv" for table in TABLES
    }
    for path in csv_paths.values():
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {path}")

    create_tables = (PROJECT_DIR / "sql/01_create_tables.sql").read_text(
        encoding="utf-8"
    )
    create_view = (PROJECT_DIR / "sql/02_create_view.sql").read_text(
        encoding="utf-8"
    )

    with psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "examples"),
        user=os.environ.get("PGUSER", "examples"),
        connect_timeout=10,
        client_encoding="UTF8",
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(create_tables)
            for table, path in csv_paths.items():
                print(f"Carregando {table}...", flush=True)
                statement = sql.SQL(
                    "COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                ).format(sql.Identifier(table))
                with path.open("rb") as source, cursor.copy(statement) as copy:
                    while block := source.read(BLOCK_SIZE):
                        copy.write(block)

            cursor.execute(create_view)
            cursor.execute(
                "SELECT COUNT(*), COUNT(DISTINCT pedido_id) FROM vendas"
            )
            item_count, order_count = cursor.fetchone()

    return item_count, order_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cria as tabelas, importa os CSVs da Olist e cria a view vendas."
    )
    parser.add_argument(
        "csv_dir",
        nargs="?",
        type=Path,
        default=PROJECT_DIR / "data",
        help="Pasta com os quatro CSVs da Olist (padrão: data/ do projeto).",
    )
    args = parser.parse_args()

    try:
        item_count, order_count = load_data(args.csv_dir)
    except (OSError, psycopg.Error) as error:
        print(f"Erro ao carregar os dados: {error}", file=sys.stderr)
        return 1

    print(f"Carga concluída: {item_count} itens e {order_count} pedidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
