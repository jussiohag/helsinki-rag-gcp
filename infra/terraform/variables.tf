variable "project" {
  description = "GCP project id. No default: keeps a real project id out of tracked files."
  type        = string
}

variable "region" {
  description = "Region for Cloud Run, BigQuery and the Artifact Registry repo."
  type        = string
  default     = "europe-north1"
}

variable "search_location" {
  description = "Location for Vertex AI Search resources. 'eu' is the only multi-region option covering europe-north1."
  type        = string
  default     = "eu"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "hrag-api"
}

variable "image" {
  description = "Fully qualified container image, e.g. europe-north1-docker.pkg.dev/PROJECT/hrag/hrag-api:TAG. Passed by deploy.sh after the build."
  type        = string
}

variable "min_instances" {
  description = "Cloud Run v2 minimum instance count."
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Cloud Run v2 maximum instance count."
  type        = number
  default     = 10
}

variable "concurrency" {
  description = "Max concurrent requests per Cloud Run instance."
  type        = number
  default     = 40
}

variable "ingress" {
  description = "Cloud Run ingress setting. Defaults to internal + load balancer; set to INGRESS_TRAFFIC_ALL for a public demo."
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
}

variable "vertex_serving_config" {
  description = "Vertex AI Search serving config resource name for HRAG_VERTEX_SERVING_CONFIG. Left empty by default because it depends on the data store/engine ids created below; deploy.sh or a tfvars file supplies the real value after first apply."
  type        = string
  default     = ""
}

variable "model_armor_template" {
  description = "Model Armor template resource name for HRAG_MODEL_ARMOR_TEMPLATE. Model Armor templates are not managed by this module (separate onboarding); pass the existing template's resource name."
  type        = string
  default     = ""
}

variable "gemini_model" {
  description = "Gemini model id for HRAG_GEMINI_MODEL."
  type        = string
  default     = "gemini-2.5-flash"
}

variable "bq_dataset_id" {
  description = "BigQuery dataset id for the turn log."
  type        = string
  default     = "hrag"
}

variable "bq_table_id" {
  description = "BigQuery table id for the turn log."
  type        = string
  default     = "turns"
}

# CMEK: pass a non-empty key resource name here to encrypt the Artifact
# Registry repo, the Cloud Run service, and the BigQuery dataset with a
# customer-managed key instead of Google-managed encryption. Left optional
# (empty default) because CMEK requires a Cloud KMS key ring provisioned
# and IAM-bound ahead of this module; see main.tf for the attach points.
variable "kms_key_name" {
  description = "Optional Cloud KMS key resource name for CMEK. Empty string disables CMEK."
  type        = string
  default     = ""
}
