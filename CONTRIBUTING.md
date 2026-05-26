# Contributing

Open Roots Graph is intended for local-first genealogy cleanup and research. Contributions should keep private data out of the repository and make the project easier to run with a user's own GEDCOM export.

## Development

1. Fork or branch from `main`.
2. Keep changes focused and include tests or validation notes.
3. Do not commit real GEDCOM exports, `.env` files, database dumps, generated audit outputs, or source material from private family trees.
4. Run backend and frontend checks before opening a pull request.

Backend:

```bash
cd backend
python3 -m compileall app scripts
pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## Data Fixtures

Use only synthetic examples under `examples/`. If a bug requires real data to reproduce, reduce it to a minimal synthetic GEDCOM fixture before sharing it.

