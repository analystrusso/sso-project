.PHONY: up down restart build logs status seed init certs help

help:
	@echo "Available commands:"
	@echo "  make up       - Start all containers"
	@echo "  make down     - Stop and remove containers"
	@echo "  make fresh    - Full teardown and rebuild from scratch"
	@echo "  make build    - Rebuild containers"
	@echo "  make logs     - Follow logs for all containers"
	@echo "  make status   - Show container status"
	@echo "  make certs    - Generate TLS certificates"
	@echo "  make seed     - Seed LDAP directory"
	@echo "  make init     - Initialize Keycloak (set secrets, sync users)"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up -d --build

logs:
	docker compose logs -f

status:
	docker compose ps

certs:
	bash certs/generate.sh

seed:
	bash ldap/seed.sh

init:
	bash keycloak/init.sh

fresh:
	docker compose down -v
	docker compose up -d --build
	bash ldap/seed.sh
	bash keycloak/init.sh
