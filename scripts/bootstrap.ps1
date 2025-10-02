git lfs install
pip install -U pip
pip install -r requirements.txt
pre-commit install
docker compose -f infra/docker-compose.yml up -d --build
