output "service_url" {
  description = "Cloud Run service URL."
  value       = google_cloud_run_v2_service.hrag.uri
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository for hrag images, e.g. europe-north1-docker.pkg.dev/PROJECT/hrag."
  value       = "${var.region}-docker.pkg.dev/${var.project}/${google_artifact_registry_repository.hrag.repository_id}"
}

output "bq_table" {
  description = "Fully qualified BigQuery table id for the turn log."
  value       = local.bq_table_ref
}

output "vertex_serving_config" {
  description = "Vertex AI Search serving config resource name in effect."
  value       = local.vertex_serving_config
}
