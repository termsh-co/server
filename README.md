# termsh server

Zero-knowledge sync API for [termsh](https://termsh.co). Stores **encrypted blobs only** — never plaintext credentials or vault master passwords.

## License

Copyright (C) 2026 termsh contributors.

Licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0).  
If you modify this software and run it as a network service, you must offer corresponding source to users interacting with it over the network. See [NOTICE](NOTICE) and [CONTRIBUTING.md](CONTRIBUTING.md).

## Requirements

- Python 3.12+
- PostgreSQL 16+

## Setup

```bash
brew install postgresql@16   # macOS example
brew services start postgresql@16
createuser termsh --createdb 2>/dev/null || true
createdb -O termsh termsh 2>/dev/null || true

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit DATABASE_URL and JWT_SECRET in .env
```

## Run

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://127.0.0.1:8000/health

Tables are created automatically on startup (development). Use Alembic migrations for production when ready.

## Environment

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `JWT_SECRET` | API token signing — **never commit** |

## Security

See [SECURITY.md](SECURITY.md) and [SECURITY_MODEL.md](SECURITY_MODEL.md).
