# ───────────────────────────────────────────────────────────────
# Autonomous Analytics Agents — Terraform Infrastructure as Code (IaC)
# ───────────────────────────────────────────────────────────────
#
# Provisions everything needed on GCP:
#   • Cloud Run service (serverless container hosting)
#   • Cloud Storage bucket (file persistence)
#   • Secret Manager (API keys)
#   • Artifact Registry (Docker images)
#   • Service accounts + IAM bindings
#
# Usage:
#   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
#   # Edit terraform.tfvars with your values
#   cd terraform
#   terraform init
#   terraform plan
#   terraform apply
# ───────────────────────────────────────────────────────────────

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Optional: store state in GCS
  # backend "gcs" {
  #   bucket = "analytics-agents-tfstate"
  #   prefix = "terraform/state"
  # }
}

# ── Provider ───────────────────────────────────────────────────
provider "google" {
  project = var.project_id
  region  = var.region
}

# ── APIs ───────────────────────────────────────────────────────
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
  ])
  service = each.key
  disable_on_destroy = false
}

# ── Service Account for Cloud Run ──────────────────────────────
resource "google_service_account" "analytics_sa" {
  account_id   = "analytics-agents-sa"
  display_name = "Autonomous Analytics Agents Cloud Run Service Account"
}

# Allow Cloud Run SA to access secrets
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.analytics_sa.email}"
}

# Allow Cloud Run SA to use GCS
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.analytics_sa.email}"
}

# ── Cloud Storage bucket ───────────────────────────────────────
resource "google_storage_bucket" "data" {
  name          = "${var.project_id}-analytics-agents-storage"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
}

# ── Secret Manager ─────────────────────────────────────────────
resource "google_secret_manager_secret" "api_keys" {
  for_each = var.api_keys

  secret_id = each.key
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "api_keys" {
  for_each = var.api_keys

  secret      = google_secret_manager_secret.api_keys[each.key].id
  secret_data = each.value
}

# ── Artifact Registry ──────────────────────────────────────────
resource "google_artifact_registry_repository" "docker" {
  repository_id = "analytics-agents"
  location      = var.region
  format        = "DOCKER"
}

# ── Cloud Run Service ──────────────────────────────────────────
resource "google_cloud_run_v2_service" "analytics_agents" {
  name     = "analytics-agents"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.analytics_sa.email

    containers {
      image = "us-central1-docker.pkg.dev/${var.project_id}/analytics-agents/analytics-agents:latest"

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }

      dynamic "env" {
        for_each = {
          GCP_PROJECT     = var.project_id
          GCS_BUCKET_NAME = google_storage_bucket.data.name
          LLM_PROVIDER    = "openai"
        }
        content {
          name  = env.key
          value = env.value
        }
      }

      # Mount secrets as env vars
      dynamic "env" {
        for_each = var.api_keys
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.api_keys[env.key].secret_id
              version = "latest"
            }
          }
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    timeout = "900s"
  }
}

# ── Public access (no auth) ────────────────────────────────────
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_v2_service.analytics_agents.location
  project  = var.project_id
  service  = google_cloud_run_v2_service.analytics_agents.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Outputs ────────────────────────────────────────────────────
output "cloud_run_url" {
  value       = google_cloud_run_v2_service.analytics_agents.uri
  description = "URL of the deployed Autonomous Analytics Agents service"
}

output "gcs_bucket" {
  value       = "gs://${google_storage_bucket.data.name}"
  description = "Cloud Storage bucket for file persistence"
}

output "artifact_registry" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/analytics-agents"
  description = "Artifact Registry Docker repository"
}
