# Dashboard Olist — Apache Superset

Projeto prático de validação do **Apache Superset 6.1.0**, com dados públicos de comércio eletrônico da Olist. A análise reúne **98.666 pedidos com itens e 112.650 itens vendidos**.

Este repositório contém os dados usados, o importador Python, a modelagem SQL, o complemento de configuração do ambiente e os YAMLs do dashboard **Olist - Vendas**. O ZIP necessário para importá-lo no Superset é gerado localmente a partir desses YAMLs.

## 1. De onde vem cada parte

| Componente | Origem e função |
|---|---|
| Superset, interface e lógica da aplicação | [Projeto oficial da Apache](https://github.com/apache/superset/tree/6.1.0). A imagem oficial fornece a aplicação preparada para executar. |
| PostgreSQL e Redis | Imagens usadas pelo Compose oficial para banco de dados, cache e tarefas. |
| Base de dados | [Brazilian E-Commerce Public Dataset by Olist, no Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). |
| Importação e modelagem | Código deste projeto: Python com psycopg, criação das tabelas e view SQL. |
| Gráficos e dashboard | Configurados no Superset para este projeto; os YAMLs da exportação ficam versionados em `dashboard/`. |
| Ajustes do ambiente | `docker-compose.olist.yml`, deste repositório, publica a porta do PostgreSQL e configura sua memória compartilhada. |

Usamos o Superset oficial como dependência, sem manter um fork. O clone da Apache fornece os arquivos de inicialização e permite consultar o código-fonte; a aplicação executada vem da **imagem Docker oficial**, selecionada com `TAG=6.1.0`. Editar o frontend clonado não modifica automaticamente a interface dessa imagem.

Uma **imagem** é o pacote preparado para executar um programa; um **container** é uma execução desse pacote. O Docker Compose descreve como iniciar os serviços e conectá-los. As imagens são baixadas durante a instalação, não armazenadas neste GitHub.

## 2. Estrutura do projeto

```text
superset-olist/
├── data/                        # Quatro CSVs originais utilizados
├── dashboard/                   # Configurações legíveis do painel
│   ├── metadata.yaml
│   ├── databases/               # Conexão com o PostgreSQL
│   ├── datasets/                # Colunas e métricas da view vendas
│   ├── charts/                  # Cinco gráficos
│   └── dashboards/              # Organização do painel e filtro
├── docker-compose.olist.yml     # Complemento ao Compose oficial
├── requirements.txt            # Dependência do importador Python
├── scripts/
│   └── load_olist.py            # Cria tabelas, importa CSVs e cria a view
├── sql/
│   ├── 01_create_tables.sql
│   └── 02_create_view.sql
└── README.md
```

## 3. O caminho dos dados e os seis containers

```text
CSVs locais → Python + psycopg → PostgreSQL → view vendas
                                                ↑
Navegador em localhost:8088 ↔ Superset ───────────┘
```

O Python lê os arquivos SQL e envia seus comandos e os CSVs ao PostgreSQL. Depois, o Superset consulta a view para produzir os gráficos. O navegador recebe os arquivos da interface e executa seu JavaScript para desenhar a tela.

O Compose oficial define **seis containers**, usando três imagens principais: Superset, PostgreSQL e Redis.

| Container | O que faz |
|---|---|
| `superset_app` | Executa a aplicação web, atende o navegador e disponibiliza a interface, os gráficos e os dashboards na porta `8088`. |
| `superset_db` | Executa o PostgreSQL. O banco `superset` guarda usuários, conexões e configurações dos gráficos; o banco `examples` recebe as tabelas da Olist. |
| `superset_cache` | Executa o Redis, usado para cache e comunicação das tarefas em segundo plano. |
| `superset_worker` | Executa tarefas em segundo plano com Celery, como trabalhos assíncronos e relatórios, quando configurados. |
| `superset_worker_beat` | Agenda tarefas periódicas e as envia para o worker executar. |
| `superset_init` | Prepara o banco interno do Superset, cria o administrador e configura permissões. Encerra ao concluir; o estado `Exited (0)` é esperado. |

A aplicação, o inicializador, o worker e o agendador usam a **mesma imagem do Superset**, iniciada com comandos diferentes. Os outros cinco containers permanecem em execução após a inicialização.

```text
superset_app ──→ superset_db
      │          ├── banco superset: configuração da ferramenta
      │          └── banco examples: dados da Olist
      ↓
superset_cache ←→ superset_worker
      ↑
superset_worker_beat

superset_init → prepara a instalação e encerra
```

O importador Python roda na máquina local e acessa `localhost:5432`. A aplicação Superset roda na rede dos containers e acessa `db:5432`. São dois endereços para chegar ao mesmo PostgreSQL, a partir de lugares diferentes. O Python não chama comandos Docker: conecta diretamente ao banco com psycopg.

Os **volumes** `db_home`, `superset_home` e `redis` preservam os arquivos dos serviços fora do ciclo de vida dos containers. Recriar o container não apaga o volume do banco.

## 4. Base de dados e modelagem

Os dados são de autoria da **Olist** e vêm do conjunto público indicado na seção de origem. A pasta `data/` contém cópias integrais, sem alterações, dos quatro arquivos usados:

- [Clientes](./data/olist_customers_dataset.csv): identificação e localização dos clientes.
- [Produtos](./data/olist_products_dataset.csv): categorias e características dos produtos.
- [Pedidos](./data/olist_orders_dataset.csv): status e datas dos pedidos.
- [Itens dos pedidos](./data/olist_order_items_dataset.csv): produtos, preços e fretes de cada item.

Os outros cinco arquivos do conjunto original não participam desta implementação.

O [SQL de criação](./sql/01_create_tables.sql) define tipos e chaves estrangeiras. Elas garantem, por exemplo, que um item aponte para um pedido existente. Por isso a carga segue a ordem clientes → produtos → pedidos → itens.

A [view vendas](./sql/02_create_view.sql) é uma consulta salva que reúne as quatro tabelas por meio de `JOIN`, ligando seus identificadores. Ela não copia os dados: o PostgreSQL executa a consulta quando a view é consultada. Também traduz os status, organiza categorias e calcula preço com frete, dias de entrega e atraso.

**Cada linha da view representa um item, não um pedido.** Um pedido com três itens aparece em três linhas. Para contar pedidos sem duplicidade, usamos `COUNT(DISTINCT pedido_id)`.

No Superset, um **dataset** registra a fonte dos gráficos, suas colunas e métricas. Aqui ele aponta para `public.vendas`.

| Métrica | Expressão SQL | Significado |
|---|---|---|
| Pedidos | `COUNT(DISTINCT pedido_id)` | Pedidos únicos presentes na view |
| Faturamento (R$) | `SUM(valor_total)` | Preço dos itens mais frete |
| Ticket médio (R$) | `SUM(valor_total) / COUNT(DISTINCT pedido_id)` | Valor médio por pedido |
| Dias de entrega (média) | `AVG(dias_entrega)` | Média do prazo sobre as linhas da view |

O indicador chamado **Faturamento** no painel soma preço e frete; não consulta pagamentos nem desconta cancelamentos automaticamente. A média de entrega é calculada por linha de item, então pedidos com mais itens têm maior peso. Os resultados descrevem essa base histórica, não o comércio eletrônico atual.

## 5. Reproduzir a instalação

### Pré-requisitos

- Git, Docker e Docker Compose atualizado, com suporte a `env_file` com `path` e `required`.
- Python 3.10 ou superior, com `venv` e `pip`.
- Acesso à internet para baixar os repositórios, imagens e dependências.
- Portas locais `8088` e `5432` disponíveis. Os comandos abaixo são para um terminal Linux ou macOS.

O ambiente descrito é uma demonstração local. As credenciais de exemplo fazem parte desse ambiente. Consulte também a [instalação oficial com Docker Compose](https://superset.apache.org/docs/installation/docker-compose/).

### Passo 1 — Baixar os dois repositórios

Execute em uma pasta nova de trabalho, sem uma instalação anterior do Superset:

```bash
git clone https://github.com/dvsantoss/superset-olist.git
git clone --depth=1 --branch 6.1.0 https://github.com/apache/superset.git
```

A estrutura deve ficar assim:

```text
pasta-de-trabalho/
├── superset/          # Código e inicialização oficiais da Apache
└── superset-olist/    # Dados, código da análise e complemento do ambiente
```

O código oficial usado como referência corresponde à tag `6.1.0`, commit `c83fb2bb1dcfac41ac51bcebd82471f4a7180d18`. Fixar a versão evita que um clone futuro traga alterações incompatíveis com este roteiro.

### Passo 2 — Preparar e iniciar o Superset

Entre na pasta oficial recém-clonada:

```bash
cd superset
printf 'SUPERSET_LOAD_EXAMPLES=no\n' > docker/.env-local
printf 'psycopg2-binary>=2.9,<3\n' > docker/requirements-local.txt
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml -f ../superset-olist/docker-compose.olist.yml up -d
```

O primeiro arquivo desativa os dashboards de exemplo. O segundo declara o driver PostgreSQL usado pelo backend do Superset; o inicializador oficial instala essa dependência. Ele é separado do **psycopg 3**, instalado depois no ambiente virtual do nosso Python.

O segundo `-f` aplica o complemento deste projeto ao Compose oficial. Assim, a porta do PostgreSQL e os `256 MiB` de memória compartilhada ficam registrados neste repositório, sem editar o Compose da Apache. Os caminhos internos do Compose continuam relativos à pasta do primeiro arquivo, `superset/`.

Ainda em `superset/`, acompanhe a inicialização:

```bash
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml -f ../superset-olist/docker-compose.olist.yml ps -a
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml -f ../superset-olist/docker-compose.olist.yml logs --tail=50 superset-init
```

Aguarde `superset_init` terminar com código `0` e a aplicação ficar disponível. A primeira execução pode demorar para baixar as imagens e instalar dependências.

Abra **http://localhost:8088** e entre com usuário `admin` e senha `admin`.

### Passo 3 — Importar os dados com Python

Saindo de `superset/`, entre no repositório da análise:

```bash
cd ../superset-olist
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PGPASSWORD=examples python scripts/load_olist.py ./data
```

O resultado esperado é:

```text
Carga concluída: 112650 itens e 98666 pedidos.
```

#### Entender a dependência do Python

O arquivo `requirements.txt` contém `psycopg[binary]>=3.2,<4`. Essa linha orienta o `pip` sobre o que instalar:

| Parte | Significado |
|---|---|
| `psycopg` | Biblioteca que permite ao Python conectar ao PostgreSQL, executar SQL e enviar os CSVs. |
| `[binary]` | Extra de instalação que inclui a implementação compilada e as bibliotecas cliente necessárias, como `libpq`, em plataformas compatíveis. Evita precisar compilar esses componentes na máquina. |
| `>=3.2` | Aceita a versão 3.2 ou superior. |
| `<4` | Não aceita versões 4 ou superiores. |
| `,` | As duas condições de versão precisam ser atendidas ao mesmo tempo. |

Por exemplo, `3.2.0` e `3.3.8` atendem à regra; `3.1.9` e `4.0.0` não. Os números são versões da biblioteca, não do PostgreSQL nem do Python. O limite superior evita uma atualização automática para uma nova versão principal que possa mudar a API; não fixa uma versão exata.

Aqui, **binary** significa código já compilado, pronto para executar. Esse extra não instala o servidor PostgreSQL: ele fornece componentes do cliente, que se conecta ao servidor já iniciado pelo Docker. No código, continuamos usando `import psycopg`.

Referências: [instalação do psycopg](https://www.psycopg.org/psycopg3/docs/basic/install.html) e [especificação de dependências Python](https://packaging.python.org/en/latest/specifications/dependency-specifiers/).

#### O que o importador executa

O [importador](./scripts/load_olist.py) confere os quatro CSVs, lê os dois arquivos SQL, conecta ao banco e importa os arquivos com `COPY FROM STDIN`, em blocos de 1 MiB. Isso dispensa carregar cada CSV inteiro na memória.

**A carga substitui as quatro tabelas e a view existentes.** Ela usa uma única transação: o PostgreSQL confirma as alterações ao concluir ou as desfaz se uma etapa falhar.

Sem o argumento `./data`, o script encontra automaticamente a pasta `data/` do projeto. A conexão aceita estas variáveis:

| Variável | Padrão ou origem |
|---|---|
| `PGHOST` | `localhost` |
| `PGPORT` | `5432` |
| `PGDATABASE` | `examples` |
| `PGUSER` | `examples` |
| `PGPASSWORD` | Senha informada no ambiente; também é possível usar `.pgpass` |

Para usar outra porta, defina `DATABASE_PORT` no terminal ao executar o Compose e use esse mesmo valor em `PGPORT` no Python. A comunicação interna do Superset continua usando `db:5432`.

### Passo 4 — Importar o dashboard

Ainda em `superset-olist/`, gere o pacote usando o próprio Python, sem dependências adicionais:

```bash
python3 -m zipfile -c dashboard_olist_vendas.zip dashboard
```

O comando compacta a pasta `dashboard/`, incluindo sua estrutura de subpastas. O pacote contém `dashboard/metadata.yaml`, `dashboard/charts/` e as demais configurações esperadas pelo importador do Superset. O arquivo gerado é ignorado pelo Git.

1. No Superset, abra **Dashboards** e escolha **Import**.
2. Selecione o arquivo local `dashboard_olist_vendas.zip`, gerado no comando anterior.
3. Quando a importação solicitar a senha da conexão **Olist (PostgreSQL)**, informe `examples`. O arquivo exportado contém `XXXXXXXXXX` no lugar da senha; esse texto não é a senha do banco.
4. Conclua a importação e abra **Olist - Vendas**.
5. Se necessário, confira a conexão em **Settings → Database Connections**: PostgreSQL, host `db`, porta `5432`, banco `examples`, usuário `examples` e senha `examples`.
6. Aplique **Estado = RN**, aguarde os cinco gráficos atualizarem e depois limpe o filtro.

A importação do ZIP registra a conexão, o dataset, as métricas, os gráficos e o painel. Não é necessário recuperar o programa temporário que originalmente criou essas configurações pela API.

## 6. Gráficos e resultados

O dashboard tem um filtro global por **Estado** e cinco visualizações:

| Gráfico | O que observar |
|---|---|
| Faturamento total | Aproximadamente R$ 15,84 milhões em preço dos itens mais frete. |
| Top 10 categorias | Beleza e Saúde aparece à frente de Relógios e Presentes e Cama, Mesa e Banho. |
| Pedidos por mês | Crescimento durante 2017 e pico em novembro, mês da Black Friday. O pico, por si só, não comprova sua causa. |
| Faturamento por estado | Concentração em SP, seguido por RJ e MG. |
| Dias de entrega por estado | Diferenças entre estados, com aproximadamente 8,3 dias em SP e 18,9 dias no RN. |

No filtro RN, o painel mostra aproximadamente **R$ 101,89 mil** em vendas. Confira os filtros ativos ao comparar números. O gráfico mensal usa janeiro de 2017 a agosto de 2018 para evitar períodos incompletos nas bordas da base.

## 7. Como os YAMLs descrevem o dashboard

**YAML é um formato de texto para registrar configurações.** Ele usa pares de chave e valor, listas e indentação para organizar informações. A pasta [dashboard/](./dashboard/) é a fonte versionada dessas configurações; o ZIP é apenas um pacote gerado para transportá-las até a tela de importação.

Por exemplo, este recorte do dataset descreve sua fonte e uma métrica:

```yaml
table_name: vendas
schema: public
metrics:
  - metric_name: pedidos
    expression: COUNT(DISTINCT pedido_id)
```

`table_name` e `schema` indicam `public.vendas`; `metrics` é uma lista; cada item iniciado por `-` descreve uma métrica. O Superset interpreta essas configurações para reconstruir o dataset. A expressão SQL é executada no PostgreSQL quando usada em uma consulta. Os YAMLs não são os dados da Olist nem o código da interface.

Os nove arquivos estão separados por responsabilidade:

- `databases/`: conexão, com senha mascarada.
- `datasets/`: referência à view, colunas e métricas.
- `charts/`: configurações dos cinco gráficos.
- `dashboards/`: disposição das visualizações e filtro.
- `metadata.yaml`: informações da exportação.

Os campos `uuid` identificam os objetos e suas relações: um gráfico referencia seu dataset, e o painel referencia os gráficos. Preserve esses identificadores ao atualizar a mesma configuração.

**Os CSVs não estão no ZIP do dashboard.** A configuração do dataset aponta para o banco, mas não inclui suas linhas. Por isso é preciso executar a carga antes de usar o painel.

Já o **Download ZIP do GitHub** baixa uma cópia dos arquivos versionados do projeto, incluindo `data/`, os scripts e os YAMLs. Ele não inclui `dashboard_olist_vendas.zip`: após baixar e extrair o projeto, gere esse pacote com o comando do passo 4.

### Atualizar o painel publicado

1. Faça as alterações no Superset e salve o dashboard.
2. Na lista **Dashboards**, use a ação **Export** do painel.
3. Na pasta `superset-olist/`, salve a nova exportação localmente como `dashboard_olist_vendas.zip`.
4. Confira se a exportação não contém credenciais pessoais. Substitua os YAMLs de `dashboard/` pelos arquivos dessa nova exportação usando o comando abaixo:

```bash
python3 - <<'PY'
from pathlib import Path
from shutil import rmtree
from zipfile import ZipFile

output_dir = Path('dashboard')
with ZipFile('dashboard_olist_vendas.zip') as archive:
    files = []
    for entry in archive.infolist():
        if entry.is_dir():
            continue
        relative_path = Path(*Path(entry.filename).parts[1:])
        if relative_path.is_absolute() or '..' in relative_path.parts:
            raise ValueError('Caminho inválido na exportação.')
        files.append((relative_path, archive.read(entry)))
    if not files:
        raise ValueError('A exportação está vazia.')
    if output_dir.exists():
        rmtree(output_dir)
    for relative_path, content in files:
        destination = output_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
PY
```

Esse comando substitui somente a pasta `dashboard/`. Revise e versione os YAMLs atualizados; o ZIP continua local e ignorado pelo Git. Se editar os YAMLs diretamente, gere novamente o ZIP antes de importá-lo: um pacote já criado não acompanha alterações posteriores nos arquivos.

## 8. Conferir o ambiente e resolver problemas

Execute os comandos desta seção dentro de `superset/`.

**Conferir a configuração combinada, sem iniciar containers:**

```bash
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml -f ../superset-olist/docker-compose.olist.yml config --quiet
```

**Conferir os dados carregados:**

```bash
docker exec superset_db psql -U examples -d examples -c 'SELECT COUNT(*) AS itens, COUNT(DISTINCT pedido_id) AS pedidos FROM public.vendas;'
```

**Erro `could not resize shared memory segment ... No space left on device`:** confira `/dev/shm`, a área de memória compartilhada do container. Seu uso pode aumentar durante a consulta e cair após uma falha; uma medição baixa depois não descarta o problema.

```bash
docker exec superset_db df -h /dev/shm
```

O limite deve aparecer como `256M`. Se estiver em `64M`, reaplique o complemento ao container do banco:

```bash
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml -f ../superset-olist/docker-compose.olist.yml up -d --no-deps db
```

Os dados permanecem no volume `db_home`. Aguarde o banco voltar e atualize o gráfico; não é necessário importar os CSVs novamente.

Se o Python não conectar, confira se o PostgreSQL terminou de iniciar, se a porta publicada corresponde a `PGPORT` e se a senha foi informada. Se a consulta funcionar no Python, mas os gráficos não, confira a senha e o host interno `db` na conexão do Superset.

Para parar o ambiente preservando os dados:

```bash
TAG=6.1.0 docker compose -f docker-compose-image-tag.yml -f ../superset-olist/docker-compose.olist.yml stop
```

## 9. Apresentação e referências

- [Slides da apresentação no Canva](https://www.canva.com/design/DAHYjPIr_-E/9oHxt4cxzIdzcTz4kQ3RoQ/edit).
- [Código oficial do Superset na versão utilizada](https://github.com/apache/superset/tree/6.1.0).
- [Documentação de instalação com Docker Compose](https://superset.apache.org/docs/installation/docker-compose/).
- [Base pública da Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

O link da gravação será incluído quando o vídeo estiver publicado.

Para apresentar a divisão de responsabilidades: “Usamos o Apache Superset oficial como plataforma. Nosso projeto prepara os dados da Olist com Python e SQL e configura os gráficos, as métricas e o dashboard.”
