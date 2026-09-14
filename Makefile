# ---- platform detection -------------------------------------------------
ifeq ($(OS),Windows_NT)
    PY      := python
    PIP     := .venv\Scripts\pip.exe
    PYTHON  := .venv\Scripts\python.exe
    UVICORN := .venv\Scripts\uvicorn.exe
    COPY    := copy
    RMVENV  := if exist .venv rmdir /s /q .venv
else
    PY      := python3
    PIP     := ./.venv/bin/pip
    PYTHON  := ./.venv/bin/python
    UVICORN := ./.venv/bin/uvicorn
    COPY    := cp
    RMVENV  := rm -rf .venv
endif

# PGPW  = postgres superuser password (chosen at PostgreSQL install)
# APPPW = app user password (you invent it; must match DB_PASSWORD in .env)
PGPW  ?=
APPPW ?= change_me_local

.PHONY: help bootstrap install env db schema verify run test \
        up down logs ps rebuild clean

help:
	@echo "LOCAL (Stage 1, no Docker)"
	@echo "  make bootstrap PGPW=your_postgres_password   full local setup"
	@echo "  make run                                     start the API"
	@echo "  make test                                    run tests"
	@echo ""
	@echo "DOCKER (Stage 3)"
	@echo "  make up        build and start the stack"
	@echo "  make down      stop (volumes KEPT)"
	@echo "  make logs      follow logs"
	@echo "  make ps        status"
	@echo "  make rebuild   rebuild images and restart"

# ---- local, no Docker ---------------------------------------------------
bootstrap: install env db schema verify
	@echo ""
	@echo "Setup complete. Now run: make run"

install:
	$(PY) -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt

env:
	-$(COPY) .env.example .env
	@echo "Now edit .env and set DB_PASSWORD=$(APPPW)"

db:
ifeq ($(PGPW),)
	@echo "ERROR: missing postgres password."
	@echo "Run: make bootstrap PGPW=your_postgres_password"
	@exit 1
endif
	-set "PGPASSWORD=$(PGPW)" && psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE messages_db;"
	-set "PGPASSWORD=$(PGPW)" && psql -U postgres -h 127.0.0.1 -c "CREATE USER messages_app WITH PASSWORD '$(APPPW)';"
	set "PGPASSWORD=$(PGPW)" && psql -U postgres -h 127.0.0.1 -c "ALTER USER messages_app WITH PASSWORD '$(APPPW)';"
	set "PGPASSWORD=$(PGPW)" && psql -U postgres -h 127.0.0.1 -c "GRANT ALL PRIVILEGES ON DATABASE messages_db TO messages_app;"
	set "PGPASSWORD=$(PGPW)" && psql -U postgres -h 127.0.0.1 -d messages_db -c "GRANT ALL ON SCHEMA public TO messages_app;"

schema:
	set "PGPASSWORD=$(APPPW)" && psql -U messages_app -h 127.0.0.1 -d messages_db -f db/init.sql

verify:
	set "PGPASSWORD=$(APPPW)" && psql -U messages_app -h 127.0.0.1 -d messages_db -c "\d messages"

run:
	$(UVICORN) app.main:app --reload --port 5000

test:
	$(PYTHON) -m pytest -v

# ---- docker -------------------------------------------------------------
up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

rebuild:
	docker compose up -d --build --force-recreate

clean:
	$(RMVENV)
