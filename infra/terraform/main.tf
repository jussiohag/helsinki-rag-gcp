# VPC Service Controls: a service perimeter around this project restricting
# discoveryengine.googleapis.com, aiplatform.googleapis.com and
# bigquery.googleapis.com would stop the turn data and search corpus from
# leaving the perimeter via a misconfigured client. Perimeters are managed at
# the access-policy (org) level, outside this module's project-scoped
# permissions — add the project to an existing perimeter's resource list
# once one exists, rather than provisioning a new access policy here.

locals {
  apis = [
    "run.googleapis.com",
    "discoveryengine.googleapis.com",
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "modelarmor.googleapis.com",
  ]

  sa_roles = [
    "roles/discoveryengine.viewer",
    "roles/aiplatform.user",
    "roles/bigquery.dataEditor",
    "roles/logging.logWriter",
  ]

  bq_table_ref = "${var.project}.${google_bigquery_dataset.hrag.dataset_id}.${google_bigquery_table.turns.table_id}"

  # Default Vertex AI Search serving config derived from the engine created
  # below. Override with var.vertex_serving_config if the search engine is
  # managed outside this module (e.g. shared across environments).
  default_serving_config = "projects/${var.project}/locations/${var.search_location}/collections/default_collection/engines/${google_discovery_engine_search_engine.hrag.engine_id}/servingConfigs/default_search"
  vertex_serving_config  = var.vertex_serving_config != "" ? var.vertex_serving_config : local.default_serving_config
}

resource "google_project_service" "apis" {
  for_each = toset(local.apis)

  project            = var.project
  service            = each.value
  disable_on_destroy = false
}

# --- Artifact Registry ---------------------------------------------------

resource "google_artifact_registry_repository" "hrag" {
  location      = var.region
  repository_id = "hrag"
  format        = "DOCKER"
  description   = "Container images for the hrag Cloud Run service."

  # CMEK: set to encrypt image layers with a customer-managed key instead of
  # the Google-managed default. Requires the Artifact Registry service agent
  # to hold Encrypter/Decrypter on the key.
  kms_key_name = var.kms_key_name != "" ? var.kms_key_name : null

  depends_on = [google_project_service.apis]
}

# --- Service account (least privilege) ------------------------------------

resource "google_service_account" "hrag" {
  account_id   = "hrag-api"
  display_name = "hrag Cloud Run runtime identity"
}

resource "google_project_iam_member" "hrag_sa_roles" {
  for_each = toset(local.sa_roles)

  project = var.project
  role    = each.value
  member  = "serviceAccount:${google_service_account.hrag.email}"
}

# --- Cloud Run v2 -----------------------------------------------------------

resource "google_cloud_run_v2_service" "hrag" {
  name     = var.service_name
  location = var.region
  ingress  = var.ingress

  # Explicit: avoid Terraform refusing to delete a live service during
  # development. Flip to true once this serves real traffic.
  deletion_protection = false

  template {
    service_account = google_service_account.hrag.email

    # CMEK: set to run the instance's ephemeral storage under a
    # customer-managed key. Requires the Cloud Run service agent to hold
    # Encrypter/Decrypter on the key.
    encryption_key = var.kms_key_name != "" ? var.kms_key_name : null

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    max_instance_request_concurrency = var.concurrency

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      env {
        name  = "HRAG_RETRIEVER"
        value = "vertex"
      }
      env {
        name  = "HRAG_GENERATOR"
        value = "gemini"
      }
      env {
        name  = "HRAG_GUARD"
        value = "model_armor"
      }
      env {
        name  = "HRAG_TURNLOG"
        value = "bigquery"
      }
      env {
        name  = "HRAG_VERTEX_SERVING_CONFIG"
        value = local.vertex_serving_config
      }
      env {
        name  = "HRAG_BQ_TABLE"
        value = local.bq_table_ref
      }
      env {
        name  = "HRAG_MODEL_ARMOR_TEMPLATE"
        value = var.model_armor_template
      }
      env {
        name  = "HRAG_GEMINI_MODEL"
        value = var.gemini_model
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# --- Vertex AI Search (Discovery Engine), location "eu" --------------------

resource "google_discovery_engine_data_store" "hrag" {
  location          = var.search_location
  data_store_id     = "hrag-service-points"
  display_name      = "Helsinki service points"
  industry_vertical = "GENERIC"
  content_config    = "CONTENT_REQUIRED"
  solution_types    = ["SOLUTION_TYPE_SEARCH"]

  depends_on = [google_project_service.apis]
}

resource "google_discovery_engine_search_engine" "hrag" {
  engine_id      = "hrag-search"
  collection_id  = "default_collection"
  location       = var.search_location
  display_name   = "Helsinki service points search"
  data_store_ids = [google_discovery_engine_data_store.hrag.data_store_id]

  search_engine_config {
    search_tier    = "SEARCH_TIER_STANDARD"
    search_add_ons = ["SEARCH_ADD_ON_LLM"]
  }
}

# --- BigQuery turn log -------------------------------------------------------

resource "google_bigquery_dataset" "hrag" {
  dataset_id = var.bq_dataset_id
  location   = var.region

  dynamic "default_encryption_configuration" {
    for_each = var.kms_key_name != "" ? [1] : []
    content {
      kms_key_name = var.kms_key_name
    }
  }

  depends_on = [google_project_service.apis]
}

# Schema mirrors src/hrag/ports.py Turn exactly, plus an insert-time `ts`
# column the app does not set. Do not change field names/types here without
# changing Turn in lockstep — the app writes rows shaped like the dataclass.
resource "google_bigquery_table" "turns" {
  dataset_id = google_bigquery_dataset.hrag.dataset_id
  table_id   = var.bq_table_id

  schema = jsonencode([
    { name = "turn_id", type = "STRING", mode = "REQUIRED" },
    { name = "channel", type = "STRING", mode = "NULLABLE" },
    { name = "language", type = "STRING", mode = "NULLABLE" },
    { name = "question_hash", type = "STRING", mode = "NULLABLE" },
    { name = "passage_ids", type = "STRING", mode = "REPEATED" },
    { name = "cited_ids", type = "STRING", mode = "REPEATED" },
    { name = "model", type = "STRING", mode = "NULLABLE" },
    { name = "guard", type = "STRING", mode = "NULLABLE" },
    {
      name = "latency_ms", type = "RECORD", mode = "NULLABLE",
      fields = [
        { name = "guard", type = "INTEGER", mode = "NULLABLE" },
        { name = "retrieve", type = "INTEGER", mode = "NULLABLE" },
        { name = "generate", type = "INTEGER", mode = "NULLABLE" },
        { name = "log", type = "INTEGER", mode = "NULLABLE" },
        { name = "total", type = "INTEGER", mode = "NULLABLE" },
      ]
    },
    { name = "outcome", type = "STRING", mode = "NULLABLE" },
    { name = "ts", type = "TIMESTAMP", mode = "NULLABLE" },
  ])

  dynamic "encryption_configuration" {
    for_each = var.kms_key_name != "" ? [1] : []
    content {
      kms_key_name = var.kms_key_name
    }
  }
}
