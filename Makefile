SHELL := /bin/bash

PYTHON ?= python3
COMPOSE ?= docker compose
TOPIC ?= orion.baseline.telemetry.logs.v1
RATE ?= 100
DURATION ?= 30
RAMP_UP ?= 0
SERVICE_NAME ?= orion-demo-workload
SERVICE_VERSION ?= 0.1.0
ENVIRONMENT ?= local
COLLECTOR_CONFIG := collector/collector.generated.yaml
ARTIFACT_ROOT := artifacts

.PHONY: start stop status generate logs clean test render-config validate-collector smoke measure validate-local

start: render-config
	mkdir -p $(ARTIFACT_ROOT)/collector $(ARTIFACT_ROOT)/measurements $(ARTIFACT_ROOT)/workload
	chmod 0777 $(ARTIFACT_ROOT)/collector
	$(COMPOSE) up -d kafka kafka-init otel-collector
	./scripts/wait-for-baseline.sh

stop:
	$(COMPOSE) down --remove-orphans

status:
	$(COMPOSE) ps

generate:
	$(COMPOSE) run --rm --service-ports workload \
		--bootstrap-servers kafka:9092 \
		--topic $(TOPIC) \
		--rate $(RATE) \
		--duration $(DURATION) \
		--ramp-up-seconds $(RAMP_UP) \
		--service-name $(SERVICE_NAME) \
		--service-version $(SERVICE_VERSION) \
		--environment $(ENVIRONMENT)

logs:
	$(COMPOSE) logs --tail=100 -f kafka otel-collector

clean:
	$(COMPOSE) down -v --remove-orphans
	rm -rf $(ARTIFACT_ROOT)
	mkdir -p $(ARTIFACT_ROOT)/collector $(ARTIFACT_ROOT)/measurements $(ARTIFACT_ROOT)/workload
	chmod 0777 $(ARTIFACT_ROOT)/collector

test:
	$(PYTHON) -m pytest

render-config:
	$(PYTHON) -m baseline_lab.render_collector_config --output $(COLLECTOR_CONFIG)

validate-collector: render-config
	./scripts/validate-collector-components.sh

smoke:
	./scripts/smoke-test.sh

measure:
	RATE=$(RATE) DURATION=$(DURATION) RAMP_UP=$(RAMP_UP) ./scripts/measure-baseline.sh

validate-local: test render-config
	$(COMPOSE) config
	./scripts/validate-collector-components.sh
	./scripts/smoke-test.sh
