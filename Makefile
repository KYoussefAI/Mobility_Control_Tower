.PHONY: demo demo-status demo-logs demo-smoke demo-down demo-reset doctor security-check backup restore verify-restore benchmark lineage-smoke reliability-smoke capture-screenshots verify-runtime-evidence verify-prometheus-runtime verify-grafana-runtime browser-smoke verify-postgres-restore

COMPOSE = docker compose --profile demo

demo:
	$(COMPOSE) up --build -d
	./scripts/wait_for_stack.sh

demo-status:
	$(COMPOSE) ps

demo-logs:
	$(COMPOSE) logs --tail=200

demo-smoke:
	./scripts/smoke_test_stack.sh

browser-smoke:
	python scripts/browser_smoke.py

capture-screenshots:
	python scripts/capture_screenshots.py

verify-prometheus-runtime:
	python scripts/verify_prometheus_runtime.py

verify-grafana-runtime:
	python scripts/verify_grafana_runtime.py

verify-postgres-restore:
	docker compose --profile demo exec -T api python scripts/verify_postgres_restore.py

verify-runtime-evidence:
	python scripts/collect_stack_evidence.py
	python scripts/verify_airflow_runtime.py
	python scripts/verify_prometheus_runtime.py
	python scripts/verify_grafana_runtime.py
	python scripts/verify_runtime_evidence.py

demo-down:
	$(COMPOSE) down -v --remove-orphans

demo-reset:
	$(COMPOSE) down -v --remove-orphans
	rm -rf data/fixtures data/serving data/quality data/watermarks

doctor:
	python scripts/doctor.py

security-check:
	python scripts/security_check.py

backup:
	python scripts/backup.py

restore:
	test -n "$(BACKUP)" || (echo "Set BACKUP=<path>" && exit 1)
	python scripts/restore.py "$(BACKUP)"

verify-restore:
	python scripts/verify_restore.py

benchmark:
	python scripts/benchmark.py

lineage-smoke:
	python scripts/lineage_smoke.py

reliability-smoke:
	test -n "$(DB)" || (echo "Set DB=<serving duckdb path>" && exit 1)
	python scripts/smoke_test_reliability_views.py "$(DB)"
