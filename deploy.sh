#!/usr/bin/env bash
# Builds the container on Cloud Build, pushes it to Artifact Registry, then
# applies the Terraform module with that image. Not executed by CI or by
# this repo's tooling — run by hand once a GCP project is provisioned.
set -euo pipefail

PROJECT="${HRAG_PROJECT:?set HRAG_PROJECT to the target GCP project id}"
REGION="${HRAG_REGION:-europe-north1}"
REPO="hrag"
IMAGE_NAME="hrag-api"
TAG="$(git rev-parse --short HEAD)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT}/${REPO}/${IMAGE_NAME}:${TAG}"

echo "Building ${IMAGE} with Cloud Build..."
gcloud builds submit \
  --project "${PROJECT}" \
  --tag "${IMAGE}" \
  .

echo "Applying Terraform with image=${IMAGE}..."
terraform -chdir=infra/terraform apply \
  -var "project=${PROJECT}" \
  -var "region=${REGION}" \
  -var "image=${IMAGE}"

URL="$(terraform -chdir=infra/terraform output -raw service_url)"
echo "Deployed: ${URL}"
