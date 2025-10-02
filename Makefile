SHELL := /bin/bash

up:
	docker compose -f infra/docker-compose.yml up --build -d app sync cron

down:
	docker compose -f infra/docker-compose.yml down

rebuild:
	docker compose -f infra/docker-compose.yml build --no-cache

logs:
	docker compose -f infra/docker-compose.yml logs -f --tail=200

snap:
	git add -A && git commit -m "chore: manual snapshot" || true && git push

lint:
	pre-commit run --all-files

reset:
	git clean -xfd && git reset --hard

db:
	python scripts/db_init.py
