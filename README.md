# Dashboard Olist E-Commerce — Apache Superset

Projeto prático de validação do **Apache Superset**.

---

## 1. Sobre o Projeto

Este repositório contém os scripts de modelagem SQL, automação de carga no **PostgreSQL** e a exportação completa do dashboard **"Olist - Vendas"** construído no **Apache Superset 6.1.0**, analisando **98.666 pedidos reais** (112.650 itens vendidos) do dataset público brasileiro da Olist.

### Estrutura do Repositório

```text
superset-olist/
├── dashboard_olist_vendas.zip   # Export oficial do Superset (conexão, dataset, métricas, 5 gráficos e filtro)
├── scripts/
│   └── load_olist.sh            # Script automatizado para criar tabelas, importar CSVs e criar a view no PostgreSQL
├── sql/
│   ├── 01_create_tables.sql     # Criação das 4 tabelas relacionais (customers, products, orders, order_items)
│   └── 02_create_view.sql       # Criação da view analítica "vendas" com joins e colunas calculadas
└── README.md
```

---

## 2. Conjunto de Dados e Modelagem

- **Fonte:** [Brazilian E-Commerce Public Dataset by Olist (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
- **Tabelas utilizadas:** `olist_customers_dataset.csv`, `olist_products_dataset.csv`, `olist_orders_dataset.csv` e `olist_order_items_dataset.csv`.
- **View analítica (`public.vendas`):** Une as 4 tabelas relacionais, traduz os status dos pedidos para português, calcula o valor total do item (`preco + frete`), o prazo real de entrega em dias (`dias_entrega`) e se houve atraso (`atrasado`).

### Métricas Configuradas no Superset

| Métrica | Expressão SQL | Descrição |
|---|---|---|
| **Pedidos** | `COUNT(DISTINCT pedido_id)` | Total de pedidos únicos (evita duplicidade em pedidos com múltiplos itens) |
| **Faturamento (R$)** | `SUM(valor_total)` | Receita total somando preço do produto e frete |
| **Ticket médio (R$)** | `SUM(valor_total) / COUNT(DISTINCT pedido_id)` | Valor médio gasto por pedido |
| **Dias de entrega (média)** | `AVG(dias_entrega)` | Tempo médio entre a compra e a entrega ao cliente |

---

## 3. Gráficos e Principais Insights

O dashboard **"Olist - Vendas"** conta com filtro interativo global por **Estado (`estado`)** e 5 visualizações principais:

1. **Faturamento Total (*Big Number*):** Receita consolidada de **R$ 15,84 milhões** em vendas (no recorte `Estado = RN`, **R$ 101,89 mil**).
2. **Top 10 Categorias (*Horizontal Bar Chart*):** Liderança de **beleza saude** (~R$ 1,44 mi), seguida por **relogios presentes** e **cama mesa banho**.
3. **Pedidos por Mês (*Line Chart*):** Evolução contínua ao longo de 2017 com pico histórico em **novembro de 2017 (Black Friday)** com 7.451 pedidos no mês.
4. **Faturamento por Estado (*Bar Chart*):** Forte concentração na região Sudeste, com **SP** em 1º lugar isolado (~R$ 5,9 mi), seguido por RJ e MG.
5. **Dias de Entrega por Estado (*Bar Chart*):** Evidencia o impacto logístico da distância — estados do Norte e Nordeste levam de **19 a 28 dias** (RN com média de **~18,9 dias**), enquanto **SP** recebe em **~8,3 dias**.

---

## 4. Como Reproduzir o Ambiente

### Pré-requisitos
- **Docker** e **Docker Compose** instalados;
- Arquivos CSV do dataset da Olist baixados em uma pasta local (ex.: `../archive/`).

### Passo 1 — Subir o Apache Superset via Docker Compose
A partir do repositório oficial do Apache Superset:

```bash
git clone --depth=1 https://github.com/apache/superset.git
cd superset
echo "SUPERSET_LOAD_EXAMPLES=no" >> docker/.env-local
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml up -d
```

Acesse `http://localhost:8088` com usuário `admin` e senha `admin`.

### Passo 2 — Carregar os dados no PostgreSQL
De dentro da pasta `superset-olist/`, execute o script passando o caminho para os CSVs baixados do Kaggle:

```bash
chmod +x scripts/load_olist.sh
./scripts/load_olist.sh ../archive
```

O script cria as 4 tabelas no banco `examples` do container `superset_db`, importa os ~112 mil registros via `\copy` em poucos segundos e cria a view `public.vendas`.

### Passo 3 — Importar o Dashboard Pronto no Superset
1. No Superset (`http://localhost:8088`), acesse o menu **Dashboards**;
2. No canto superior direito, clique no ícone de **Importar** (seta para cima ao lado de *+ Dashboard*);
3. Selecione o arquivo [`dashboard_olist_vendas.zip`](./dashboard_olist_vendas.zip) deste repositório e clique em **Import**;
4. Abra o dashboard **Olist - Vendas** e utilize a barra lateral **Filters** para filtrar por qualquer estado brasileiro.
