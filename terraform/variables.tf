# ── Required Variables ─────────────────────────────────────────

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "api_keys" {
  description = "Map of API key secret names to their values"
  type        = map(string)
  sensitive   = true
  default     = {}
  # Example:
  # api_keys = {
  #   OPENAI_API_KEY    = "sk-..."
  #   ANTHROPIC_API_KEY = "sk-ant-..."
  #   GROQ_API_KEY      = "gsk_..."
  # }
}
