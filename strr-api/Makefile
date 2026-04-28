.PHONY: lint
.PHONY: build

MKFILE_PATH:=$(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_ABS_DIR:=$(patsubst %/,%,$(dir $(MKFILE_PATH)))

PROJECT_NAME:=strr_api
DOCKER_NAME:=strr-api

#################################################################################
# COMMANDS -- Setup                                                             #
#################################################################################

clean-pyc: ## Clean cache files
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

#################################################################################
# COMMANDS - CI                                                                 #
#################################################################################
pisort:
	poetry run isort . --check -v

pblack:
	poetry run black . --check

pylint: ## Linting with pylint
	pylint --rcfile=setup.cfg src/$(PROJECT_NAME)

flake8: ## Linting with flake8 ## tests
	flake8 src/$(PROJECT_NAME)

lint: fmt-check pylint flake8 ## run all lint type scripts

fmt: ## Format code with isort and black
	poetry run isort .
	poetry run black .

fmt-check: ## Check isort and black without changing files
	poetry run isort . --check
	poetry run black . --check

test: ## Unit testing
	pytest

build: ## Build the docker container
	docker build . -t $(DOCKER_NAME) \
	    --platform linux/amd64 \
	    --build-arg VCS_REF=$(shell git rev-parse --short HEAD) \
	    --build-arg BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")

build-nc: ## Build the docker container without caching
	docker build --no-cache -t $(DOCKER_NAME) .

#################################################################################
# COMMANDS - Local                                                              #
#################################################################################

migrate: ## Run Alembic migrations to head
	poetry run flask db upgrade

# Synthetic volume + /registrations/search timings (see README "Performance testing")
PERF_N ?= 10000

perf-seed: ## Insert synthetic HOST registrations (set DEPLOYMENT_ENV=development)
	DEPLOYMENT_ENV=development poetry run python scripts/perf_seed_registrations.py --registrations $(PERF_N) --batch-size 500 --seed 42

perf-bench: ## Time examiner search matrix (optional PERF_OUT=file.json)
	@if [ -z "$(PERF_OUT)" ]; then \
		DEPLOYMENT_ENV=development poetry run python scripts/benchmark_registration_search.py --iterations 3; \
	else \
		DEPLOYMENT_ENV=development poetry run python scripts/benchmark_registration_search.py --iterations 3 --output "$(PERF_OUT)"; \
	fi

perf-sql: ## Log SQL for PERF_CASE (default default_statuses_only); redirect stderr to a file
	DEPLOYMENT_ENV=development poetry run python scripts/perf_sql_registration_search.py --case $(or $(PERF_CASE),default_statuses_only)

perf-compare: ## Compare PERF_BEFORE and PERF_AFTER JSON to PERF_REPORT (Markdown)
	@test -n "$(PERF_BEFORE)" && test -n "$(PERF_AFTER)" && test -n "$(PERF_REPORT)" || (echo "Set PERF_BEFORE, PERF_AFTER, PERF_REPORT"; exit 1)
	poetry run python scripts/compare_perf_benchmarks.py --before "$(PERF_BEFORE)" --after "$(PERF_AFTER)" --output "$(PERF_REPORT)"

#################################################################################
# Self Documenting Commands                                                     #
#################################################################################
.PHONY: help perf-seed perf-bench perf-sql perf-compare migrate

.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
