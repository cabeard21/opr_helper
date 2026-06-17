# OPR Helper

Web app for building legal One Page Rules Age of Fantasy army lists and viewing probability calculations.

This repository currently contains the Phase 1 skeleton: a Django/DRF backend and a React 18 + Vite + Tailwind frontend.

## Requirements

- Python 3.13
- Node.js 24 with npm
- `make`, optional but recommended

On this Windows machine, use `cmd /c npm ...` when running npm from PowerShell because PowerShell script execution blocks the `npm.ps1` shim.

## Backend Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
.\.venv\Scripts\python backend\manage.py check
.\.venv\Scripts\python backend\manage.py runserver
```

The backend health endpoint is available at `http://127.0.0.1:8000/`.

## Frontend Setup

```powershell
cmd /c npm install --prefix frontend
cmd /c npm run dev --prefix frontend
```

The frontend dev server starts at `http://localhost:5173`.

## Common Commands

```powershell
make dev-be
make dev-fe
make check
make test
```
