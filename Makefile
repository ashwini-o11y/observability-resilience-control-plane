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
ARTIFACT_DIR := artifacts/collector

.PHONY: start stop status generate logs clean test render-config

start: render-config
	mkdir -p $(ARTIFACT_DIR)
	$(COMPOSE) up -d kafka kafka-init otel-collector

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
	rm -rf $(ARTIFACT_DIR)
	mkdir -p $(ARTIFACT_DIR)

test:
	$(PYTHON) -m pytest

render-config:
	$(PYTHON) -m baseline_lab.render_collector_config --output $(COLLECTOR_CONFIG)
