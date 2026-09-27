#!/usr/bin/env sh
set -eu

: "${KAFKA_BOOTSTRAP_SERVER:=kafka:9092}"
: "${KAFKA_TOPIC:=orion.baseline.telemetry.logs.v1}"
: "${KAFKA_TOPIC_PARTITIONS:=3}"
: "${KAFKA_TOPIC_REPLICATION_FACTOR:=1}"

echo "Waiting for Kafka broker at ${KAFKA_BOOTSTRAP_SERVER}..."
until kafka-topics --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" --list >/dev/null 2>&1; do
  sleep 2
done

echo "Ensuring topic ${KAFKA_TOPIC} exists..."
kafka-topics \
  --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" \
  --create \
  --if-not-exists \
  --topic "${KAFKA_TOPIC}" \
  --partitions "${KAFKA_TOPIC_PARTITIONS}" \
  --replication-factor "${KAFKA_TOPIC_REPLICATION_FACTOR}"

kafka-topics --bootstrap-server "${KAFKA_BOOTSTRAP_SERVER}" --describe --topic "${KAFKA_TOPIC}"
