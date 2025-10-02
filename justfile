set shell := ["/bin/bash", "-c"]

up:
	docker compose -f infra/docker-compose.yml up --build -d app sync cron

down:
	docker compose -f infra/docker-compose.yml down

logs:
	docker compose -f infra/docker-compose.yml logs -f --tail=200

lint:
	pre-commit run --all-files

snap:
	git add -A && git commit -m "chore: snapshot" || true && git push

db:
	python scripts/db_init.py
