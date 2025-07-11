terraform {
  backend "gcs" {
    bucket = "terraform_bucket_1231"
    prefix = "terraformcar/state"
  }
}

provider "google" {
  project = var.project
  region  = var.region
  zone    = var.zone
}

provider "random" {}

resource "random_pet" "random_suffix" {
  keepers = {
    project = var.project
    region  = var.region
    zone    = var.zone
  }
}

resource "google_project_service" "artifact_registry_service" {
  service                    = "artifactregistry.googleapis.com"
  disable_dependent_services = true
  disable_on_destroy         = true
}

resource "google_project_service" "container_service" {
  service                    = "container.googleapis.com"
  disable_dependent_services = true
  disable_on_destroy         = true
}

resource "google_project_service" "container_registry_service" {
  service                    = "containerregistry.googleapis.com"
  disable_dependent_services = true
  disable_on_destroy         = true
}

resource "google_service_account" "service_account" {
  account_id   = "gcs-${random_pet.random_suffix.id}-rw"
  display_name = "Service Account for RW"
  project      = var.project
}

resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "car-marketplace-repo"
  format        = "DOCKER"
  project       = var.project
  depends_on    = [google_project_service.artifact_registry_service]
}

resource "google_artifact_registry_repository_iam_binding" "repo_reader" {
  location   = var.region
  repository = google_artifact_registry_repository.docker_repo.repository_id
  project    = var.project
  role       = "roles/artifactregistry.reader"
  members = [
    "serviceAccount:${google_service_account.service_account.email}",
  ]
  depends_on = [google_service_account.service_account, google_artifact_registry_repository.docker_repo]
}

resource "google_container_cluster" "kubernetes_cluster" {
  name               = "k8s-cluster-${random_pet.random_suffix.id}"
  location           = var.zone
  initial_node_count = 1
  deletion_protection = true
  node_config {
    machine_type    = "n1-standard-4"
    image_type      = "COS_CONTAINERD"
    service_account = google_service_account.service_account.email
    oauth_scopes    = [
      "https://www.googleapis.com/auth/cloud-platform",
      "https://www.googleapis.com/auth/userinfo.email",
    ]
    disk_size_gb    = 100
    disk_type       = "pd-balanced"
    metadata = {
      "disable-legacy-endpoints" = "true"
    }
    resource_labels = {
      "goog-gke-node-pool-provisioning-model" = "on-demand"
    }
    kubelet_config {
      cpu_cfs_quota                          = false
      insecure_kubelet_readonly_port_enabled = "FALSE"
      pod_pids_limit                         = 0
    }
  }
  node_version = "1.32.4-gke.1415000"
  network_policy {
    enabled  = false
    provider = "PROVIDER_UNSPECIFIED"
  }
  private_cluster_config {
    enable_private_endpoint = false
    enable_private_nodes    = false
  }
  depends_on = [
    google_project_service.container_service,
    google_service_account.service_account,
    google_artifact_registry_repository_iam_binding.repo_reader,
  ]
}