.PHONY: migrate discover ingest-feeds ingest-ats test-pipeline test-api test dev-api

DB_URL ?= file:local.db

migrate:
	job-pipeline --db-url $(DB_URL) migrate

discover:
	job-pipeline --db-url $(DB_URL) discover

ingest-feeds:
	job-pipeline --db-url $(DB_URL) ingest-feeds

ingest-ats:
	job-pipeline --db-url $(DB_URL) ingest-ats --shard 0 --total-shards 1 --max-boards 50

test-pipeline:
	pytest -v pipeline/tests

test-api:
	cd api && npm run typecheck && npm test

test: test-pipeline test-api

dev-api:
	cd api && TURSO_DATABASE_URL=file:../local.db npm run dev
