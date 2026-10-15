#bin/bash
pg_dump -h localhost -p 5433 -U banicky -d microbites_db --schema-only -f db_schema.sql