.PHONY: up down dev-backend dev-frontend install-backend install-frontend migrate import-modules logs \
        prod prod-down prod-logs prod-ps ssl-renew ssl-status

# === DOCKER ===
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# === BACKEND ===
install-backend:
	cd backend && pip install -r requirements.txt

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	cd backend && alembic upgrade head

import-modules:
	cd backend && python -m app.scripts.import_modules

# === FRONTEND ===
install-frontend:
	npm install --prefix frontend

dev-frontend:
	npm run --prefix frontend dev

# === FULL STACK ===
dev: up
	@echo "Starting backend..."
	$(MAKE) -j2 dev-backend dev-frontend

setup: up migrate import-modules
	@echo "Setup complete. Run: make dev-backend and make dev-frontend"

# === PRODUCTION ===
prod:
	@bash deploy.sh

prod-no-build:
	@bash deploy.sh --no-build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-ps:
	docker compose -f docker-compose.prod.yml ps

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

ssl-renew:
	docker compose -f docker-compose.prod.yml run --rm certbot renew --quiet
	docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
	@echo "SSL renewed and nginx reloaded."

ssl-status:
	docker compose -f docker-compose.prod.yml run --rm certbot certificates
