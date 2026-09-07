#!/usr/bin/env bash
# Uploads build/documents.jsonl to GCS and imports it into the Vertex AI Search data
# store. Not run by CI or by `make` — infra (the data store, the bucket) is created by
# `feat/s3-infra` first; run this by hand once that exists.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-helsinki-rag-gcp}"
LOCATION="${LOCATION:-eu}"
BUCKET="${BUCKET:-gs://${PROJECT_ID}-hrag-corpus}"
DATA_STORE_ID="${DATA_STORE_ID:-helsinki-service-points}"
DOCS_FILE="${DOCS_FILE:-build/documents.jsonl}"
GCS_URI="${BUCKET}/documents.jsonl"

gcloud storage cp "${DOCS_FILE}" "${GCS_URI}"

gcloud discovery-engine documents import \
  --project="${PROJECT_ID}" \
  --location="${LOCATION}" \
  --data-store="${DATA_STORE_ID}" \
  --gcs-uri="${GCS_URI}" \
  --gcs-data-schema=document \
  --reconciliation-mode=incremental

# REST equivalent, if the gcloud component is unavailable:
#
# curl -sS -X POST \
#   -H "Authorization: Bearer $(gcloud auth print-access-token)" \
#   -H "Content-Type: application/json" \
#   "https://discoveryengine.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/collections/default_collection/dataStores/${DATA_STORE_ID}/branches/0/documents:import" \
#   -d "{\"gcsSource\": {\"inputUris\": [\"${GCS_URI}\"], \"dataSchema\": \"document\"}, \"reconciliationMode\": \"INCREMENTAL\"}"
