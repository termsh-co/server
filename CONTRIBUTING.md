# Contributing to termsh server

## License

By contributing, you agree that your contributions are licensed under the  
[GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0).

The server is network-facing software: AGPL applies when you deploy modified versions as a service.

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
