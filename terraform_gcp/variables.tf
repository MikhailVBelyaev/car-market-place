variable "project" {
  description = "ID of your GCP project"
  type        = string
}

variable "location" {
  description = "Location of GCS bucket"
  type        = string
  default     = "US"
}

variable "region" {
  description = "Region for deployment"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zone in the region for deployment"
  type        = string
  default     = "us-central1-a"
}