# Open Roots Graph

Open Roots Graph is a local-first genealogy cleanup and research workspace for GEDCOM exports. It imports family tree data into Neo4j, helps inspect people, families, places, evidence claims, conflicts, migration patterns, timelines, and research priorities, and can optionally use an LLM for read-only research assistance.

This project is designed for private local use. Your genealogy data can contain living people, family relationships, locations, source notes, and other sensitive information. Do not publish your real GEDCOM files, generated `data/` outputs, `.env` files, or database dumps.

## Features

- Import GEDCOM data into a Neo4j graph.
- Browse individuals, families, places, timelines, pedigree charts, and relationship graphs.
- Track evidence claims, source records, conflicts, research tasks, and data quality issues.
- Score research priorities for direct and collateral relatives.
- Export cleaned GEDCOM data from Neo4j.
- Optionally ask an AI research assistant to generate sanitized read-only Cypher queries.

## Stack

- Backend: Python, FastAPI, Neo4j driver
- Frontend: Next.js, React, Tailwind CSS, D3.js, Leaflet
- Database: Neo4j 5
- Local orchestration: Podman-compatible `pod.sh`

## Quick Start

### 1. Configure

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- `NEO4J_PASSWORD`
- `GEDCOM_PATH` if you want to import your own GEDCOM file
- `OPENROUTER_API_KEY` only if you want the optional AI assistant

### 2. Start services

```bash
chmod +x pod.sh
./pod.sh build
./pod.sh start
```

Services:

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

### 3. Import data

Use the synthetic fixture first:

```bash
cd backend
python3 scripts/import_tree.py --clear
```

Then set `GEDCOM_PATH` in `.env` to your private GEDCOM export and run the same command again when you are ready to import your own tree.

After importing data into Neo4j, seed the evidence layer:

```bash
python3 scripts/seed_evidence_schema.py
python3 scripts/migrate_legacy_claims.py
```

## Privacy

The repository intentionally ignores `data/`, `.env`, GEDCOM files, ZIP exports, and generated audit files. Keep real genealogy exports outside Git. The included `examples/sample-tree.ged` is synthetic and exists only as a small public fixture.

## Development

Backend:

```bash
cd backend
pip install -e ".[dev]"
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

## Data Quality Checks

See [docs/data-quality-checks.md](docs/data-quality-checks.md) for the reusable check taxonomy used to classify chronology, duplicate, source, place, topology, and privacy issues.

## Project Structure

```text
backend/            FastAPI app, Neo4j repositories, scripts
frontend/           Next.js app
docs/               Public design and data-quality guidance
examples/           Synthetic public fixtures
pod.sh              Local Podman orchestration
.env.example        Safe configuration template
```

## License

MIT
