.PHONY: up down test test-backend test-frontend dev-backend dev-frontend

up:            ## build and run the stack (UI on :8080, API on :8000)
	docker compose up --build

down:
	docker compose down

test:          ## run both test suites in isolated containers
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

test-backend:
	cd backend && pytest -q --cov=app

test-frontend:
	cd frontend && npx vitest run

dev-backend:
	cd backend && uvicorn app.main:app --reload

dev-frontend:
	cd frontend && npm run dev
