.PHONY: up down build logs status test clean

# Start the application services with Docker Compose
up:
	docker compose up --build -d

# Stop and remove containers and networks
down:
	docker compose down

# Build container images
build:
	docker compose build

# View container logs
logs:
	docker compose logs -f

# Check status of running containers
status:
	docker compose ps

# Run backend unit and integration tests inside virtual environment or container
test:
	docker compose exec -e MOCK_LLM=true -T backend pytest tests/ -v

# Clean temporary files and caches
clean:
	docker compose down -v
