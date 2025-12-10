# API Parlamento Português - *Portuguese Parliament Data API*

API REST para acesso estruturado aos dados disponibilizados pelo Parlamento, incluíndo iniciativas,
votações, deputados, partidos, círculos eleitorais.

*REST API providing structured access to Portuguese Parliament data: legislative initiatives, voting
records, deputies, parties, and electoral circles.*

## Features

* **17+ REST API Endpoints** - Initiatives, votes, deputies, parties, circles... the list will grow.
* **Filtering** - By date, party, type, author, and more (depending on the endpoint). Covers the most common tasks.
* **Fast queries** (hopefully). DuckDB on Parquet files is quite speedy, with <100ms query times for all tested queries.
* **OpenAPI documentation** - Interactive Swagger UI + ReDoc
* **Data validation** - Pydantic validation on requests/responses
* **Pagination** - Offset-based approach (max 500 per page)
* **Docker ready** - `docker-compose` manifest included.
* **Tests** -  Comprehensive test coverage

## General approach and technology stack

The project uses **FastAPI** as the building block, and should work with Python 3.12+. The ETL
pipeline is built around the JSON files provided by the official Parliament site, which are then
converted to Parquet. DuckDB is used for querying.

The information made available is an extended subset of the one contained in the source files; more
can be added in the future.


## Quick start

The `requirements.txt` provided can be used with `venv`, and if so the `Makefile` provides some help
in running tests and running the main client-facing app (uvicorn based). Take a look with `make
help` to check what's available

Check `DEPLOYMENT.md` for additional information on deployment choices
and security aspects (Cloudflare, nginx, Cloud Run, etc).

### Environment configuration

Create an `.env` file (see `.env.example`, and copy it to `.env` to get started):

```env
DUCKDB_MEMORY_LIMIT=4GB
DUCKDB_THREADS=4
```

Not everything is being configured in the `.env` file: `config.py` contains the base information
about JSON URLs, etc.

### Local Development

Using Poetry to install dependencies and run the main app:

```bash
# Install dependencies
poetry install

# Run API with auto-reload
poetry run uvicorn app.main:app --reload

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

Alterenatively, use a `venv`:

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Start the API
make run
```

### Run with Docker

A `docker-compose.yaml` file is included, so this works:

```bash
docker-compose up
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

... or build Docker image manually:

```bash
docker build -t parlamentodb .
docker run -p 8000:8000 parlamentodb
```

### Cloud Run

This project was also tested with Google Cloud Run:

```bash
gcloud run deploy parlamentodb \
  --source . \
  --platform managed \
  --region europe-west1
```

### API approach and example API Calls

In general, any endpoint that returns multiple items will include the content in a `data` element,
and also contain a `pagination` element to allow cursor-based querying. Endpoints that return single
elements will directly return the JSON of what's being requested. This is the desired behaviour and
any inconsistency, if present, will be corrected.

A detailed description of the endpoints here would risk getting stale rather quickly: use the
**interactive documentation** included

* [/docs](/docs) (Swagger UI)
* [/redoc](/redoc) (ReDoc)

The main page redirects to the Swagger UI docs

Some examples (hopefully not out of sync with the current version of the API):

```bash
# List initiatives (returns ini_id for each record)
curl 'http://localhost:8000/api/v1/iniciativas/?limit=5'

# Get a specific initiative by its unique ID
curl 'http://localhost:8000/api/v1/iniciativas/315199'

# Filter by initiative number (may return multiple results)
curl 'http://localhost:8000/api/v1/iniciativas/?ini_nr=7&legislatura=L15'

# Get all events for a specific initiative
curl 'http://localhost:8000/api/v1/iniciativas/315199/eventos'

# Filter events by type and date
curl 'http://localhost:8000/api/v1/iniciativas/315199/eventos?evento_fase=Entrada&data_desde=2025-06-01'
```

## Architecture and components

As mentioned, FastAPI is the core component used, and brings with it several other ones (Swagger, ReDoc, Startlet, Pydantic).

- **FastAPI** - Modern Python web framework with automatic OpenAPI generation
- **Pydantic** - Type validation and serialization
- **DuckDB** - Embedded analytical database (no server needed)
- **Parquet** - Columnar storage format (~26x compression vs JSON)
- **Poetry** - Dependency management



### ETL and data flow

The API uses DuckDB to query the "silver" datasets (Parquet created from the original JSON):

```
       Open Data (JSON)
             ↓
       ETL Pipeline (fetch + transform)
             ↓
       Parquet Files (data/silver/*.parquet)
             ↓
       DuckDB Queries
             ↓
       FastAPI Endpoints
             ↓
       JSON Responses
```

The used data tiers are:

1. `bronze`: the original JSON files.
2. `silver`: Parquet files, the result of the transformation process.
3. `gold`: not currently used, but reserved for files with new data (derivatives of the original one)

To run the ETL steps:

```bash
# Activate environment
source .venv/bin/activate

# Fetch latest data from parlament.pt
python -m etl.fetch

# Transform to Parquet
python -m etl.transform
```

... or `make etl-fetch` and `make etl-transform`.

## Testing

Effort has been made to add tests, using pytest. The Makefile has some useful targets:

```bash
# Run all tests
make test

# Run without property tests (faster)
make test-quick

# Run with coverage
poetry run pytest --cov=app tests/
```



## ETL Pipeline

The API serves data processed through an ETL pipeline that:
1. Fetches JSON from Portuguese Parliament Open Data
2. Normalizes field names (PascalCase → snake_case)
3. Converts to Parquet format
4. Adds metadata (legislature, etl_timestamp)

### Running the ETL

```bash
# Fetch raw JSON from parlamento.pt
poetry run python -m etl.fetch

# Transform JSON → Parquet
poetry run python -m etl.transform

# Data lands in data/silver/*.parquet
# API automatically picks up new data
```

### Data Layers

**Bronze Layer** (`data/bronze/`):
- Raw JSON downloads from parlamento.pt
- Complete preservation of source data
- Files: `iniciativas_l17.json`, `votacoes_l17.json`, etc.

**Silver Layer** (`data/silver/`):
- Normalized Parquet files
- snake_case field names
- Nested structures preserved as STRUCT/LIST types
- Files: `iniciativas_l17.parquet`, `votacoes_l17.parquet`, etc.
- Compression: ZSTD (~26x size reduction)

### Configuration

Edit `config.py` to add/modify legislatures:

```python
LEGISLATURES = {
    "L17": {
        "url": "https://app.parlamento.pt/webutils/docs/doc.txt?...",
        "name": "XVII Legislatura",
        "start_date": "2025-06-03",
    },
    # Add more legislatures here
}
```

### ETL Performance

**Overall (3 Legislatures):**
- Total records: 4,058 initiatives + 3,792 votes
- Total JSON: 114.80 MB
- Total Parquet: 4.39 MB
- Average compression: **26.18x**
- Processing time: ~5 seconds total

---

## Project Structure

```
parlamentodb/
├── app/                      # FastAPI application
│   ├── main.py              # Application entry point
│   ├── config.py            # Settings via pydantic-settings
│   ├── dependencies.py      # Shared dependencies (DuckDB connection)
│   ├── routers/             # API endpoints
│   │   ├── iniciativas.py   # /api/v1/iniciativas
│   │   ├── votacoes.py      # /api/v1/votacoes
│   │   ├── deputados.py     # /api/v1/deputados
│   │   ├── circulos.py      # /api/v1/circulos
│   │   ├── partidos.py      # /api/v1/partidos
│   │   ├── legislaturas.py  # /api/v1/legislaturas
│   │   └── health.py        # /health
│   └── models/              # Pydantic response models
├── etl/                     # ETL pipeline
│   ├── fetch.py            # Download JSON from parlamento.pt
│   ├── transform.py        # JSON → Parquet transformation
│   └── schema.py           # Field name mappings
├── data/
│   ├── bronze/             # Raw JSON files
│   └── silver/             # Normalized Parquet files
├── tests/                  # Test suite (33 tests)
├── docker-compose.yml      # Local deployment
├── Dockerfile              # Production deployment
├── pyproject.toml          # Poetry dependencies
└── README.md
```

---

## Roadmap

✅ **Phase 1: ETL Pipeline** (Complete)
- JSON fetching with retry logic
- Schema normalization
- Parquet conversion
- 26x compression achieved

✅ **Phase 2: REST API** (Complete)
- 17+ endpoints across 7 routers
- Advanced filtering (date, party, author, type)
- Pagination
- OpenAPI documentation
- Docker deployment

⏳ **Phase 3: Additional Datasets** (In Progress)
- Deputy information ✅
- Electoral circles ✅
- Parliamentary groups ✅
- Voting details with party breakdown ✅
- Historical data (all legislatures)

🔜 **Phase 4: Advanced Analytics**
- CSV export for data journalists
- Voting pattern analysis
- Party distance metrics
- Deputy voting records

---

## Data Source

**Portuguese Parliament Open Data**
https://www.parlamento.pt/Cidadania/Paginas/DadosAbertos.aspx

All data is publicly available under Portugal's open data initiative. This API provides structured access to:
- Legislative initiatives (Iniciativas)
- Voting sessions (Votações)
- Deputy information (Deputados)
- Parliamentary groups (Partidos)
- Electoral circles (Círculos)

---

## Related Projects

**Hemicycle.party** - Advanced visualizations and analytics
https://pt.hemicycle.party

A Streamlit application that consumes this API to provide:
- Voting distance heatmaps
- Party clustering analysis
- Deputy voting patterns
- Interactive visualizations

---

## License

GNU Affero General Public License v3.0.

