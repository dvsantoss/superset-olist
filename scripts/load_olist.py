import argparse  # Interpreta argumentos do terminal e gera a ajuda --help.
import os  # Lê variáveis de ambiente com as configurações do banco.
import sys  # Permite informar erros e o código de saída do programa.
from pathlib import Path  # Representa caminhos de pastas e arquivos.

import psycopg  # Conecta o Python ao PostgreSQL.
from psycopg import sql  # Monta comandos SQL com nomes de tabelas de forma segura.


PROJECT_DIR = Path(__file__).resolve().parent.parent  # Sobe de scripts/ até a raiz do projeto.
# Chaves estrangeiras exigem clientes e produtos antes de pedidos e itens.
TABLES = ("customers", "products", "orders", "order_items")
BLOCK_SIZE = 1024 * 1024  # Lê até 1 MiB do CSV por vez.


def load_data(csv_dir: Path) -> tuple[int, int]:
    # Recebe a pasta dos CSVs e retorna dois números: total de itens e de pedidos.
    # Associa cada tabela ao caminho do CSV correspondente.
    csv_paths = {
        table: csv_dir / f"olist_{table}_dataset.csv" for table in TABLES
    }
    # Confere os arquivos antes de executar o SQL que substitui as tabelas.
    for path in csv_paths.values():
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {path}")

    # Lê o texto dos arquivos SQL; os comandos só serão executados depois, no banco.
    create_tables = (PROJECT_DIR / "sql/01_create_tables.sql").read_text(
        encoding="utf-8"
    )
    create_view = (PROJECT_DIR / "sql/02_create_view.sql").read_text(
        encoding="utf-8"
    )

    # O bloco with confirma a carga ao concluir; se ocorrer erro, desfaz as alterações.
    # Usa as variáveis PG* quando definidas; a senha pode vir de PGPASSWORD ou .pgpass.
    with psycopg.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "examples"),
        user=os.environ.get("PGUSER", "examples"),
        connect_timeout=10,
        client_encoding="UTF8",
    ) as connection:
        with connection.cursor() as cursor:  # O cursor envia comandos e recebe resultados do banco.
            cursor.execute(create_tables)  # Recria as quatro tabelas, substituindo as anteriores.
            for table, path in csv_paths.items():
                print(f"Carregando {table}...", flush=True)
                # COPY recebe as linhas enviadas pelo Python; HEADER TRUE ignora o cabeçalho do CSV.
                statement = sql.SQL(
                    "COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                ).format(sql.Identifier(table))  # Trata o nome da tabela como identificador SQL.
                # Abre o CSV como bytes e inicia o envio para a tabela correspondente.
                with path.open("rb") as source, cursor.copy(statement) as copy:
                    # Envia blocos de 1 MiB, sem carregar o CSV inteiro na memória.
                    while block := source.read(BLOCK_SIZE):
                        copy.write(block)

            cursor.execute(create_view)  # Cria a view vendas, que reúne as quatro tabelas por JOIN.
            # Um pedido pode ter vários itens; DISTINCT evita contá-lo mais de uma vez.
            cursor.execute(
                "SELECT COUNT(*), COUNT(DISTINCT pedido_id) FROM vendas"
            )
            item_count, order_count = cursor.fetchone()  # Obtém os dois totais retornados pela consulta.

    return item_count, order_count


def main() -> int:
    # Configura as instruções exibidas ao executar o script com --help.
    parser = argparse.ArgumentParser(
        description="Cria as tabelas, importa os CSVs da Olist e cria a view vendas."
    )
    parser.add_argument(
        "csv_dir",
        nargs="?",  # Torna opcional informar a pasta no terminal.
        type=Path,  # Converte o argumento recebido em um caminho de arquivo ou pasta.
        default=PROJECT_DIR / "data",  # Usa data/ quando nenhuma pasta é informada.
        help="Pasta com os quatro CSVs da Olist (padrão: data/ do projeto).",
    )
    args = parser.parse_args()  # Lê a pasta informada, como em: python scripts/load_olist.py ./data.

    try:
        item_count, order_count = load_data(args.csv_dir)  # Executa a carga usando a pasta escolhida.
    except (OSError, psycopg.Error) as error:
        print(f"Erro ao carregar os dados: {error}", file=sys.stderr)
        return 1  # Informa ao terminal que a execução falhou.

    print(f"Carga concluída: {item_count} itens e {order_count} pedidos.")
    return 0  # Informa ao terminal que a execução terminou com sucesso.


if __name__ == "__main__":  # Inicia a carga apenas quando este arquivo é executado diretamente.
    sys.exit(main())
