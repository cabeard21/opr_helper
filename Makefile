PYTHON ?= .venv/Scripts/python
NPM ?= cmd /c npm

.PHONY: dev-be dev-fe test check

dev-be:
	$(PYTHON) backend/manage.py runserver

dev-fe:
	$(NPM) run dev --prefix frontend

test:
	$(PYTHON) -m pytest backend
	$(NPM) run build --prefix frontend

check:
	$(PYTHON) backend/manage.py check
	$(NPM) run build --prefix frontend
