# Solyra API

FastAPI backend for Solyra Dermocare.

## Local

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
fastapi dev app/main.py
```

## EasyPanel

Service path:

```txt
backend/
```

Port:

```txt
8000
```

Domain:

```txt
api.solyra.ma
```

Database:

```bash
DATABASE_URL=postgresql+asyncpg://solyra:solyra@solyra_database:5432/solyra
ALEMBIC_DATABASE_URL=postgresql://solyra:solyra@solyra_database:5432/solyra
```

Startup is handled by `scripts/entrypoint.sh`:

```bash
alembic upgrade head
fastapi run app/main.py --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `GET /v1/health`
- `POST /v1/orders`
- `PATCH /v1/orders/{order_number}/status`
