# Provision RKE
resource "rke_cluster" "cluster" {
  cloud_provider {
    name = "openstack"
    openstack_cloud_config {
      global {
        username    = var.os_username
        password    = var.os_password
        auth_url    = var.os_auth_url
        tenant_id   = var.os_project_id
        tenant_name = var.os_project_name
        domain_name = var.os_user_domain_name
      }
      block_storage {
        bs_version        = "auto"
        ignore_volume_az  = "true"
        trust_device_path = "false"
      }
    }
  }

dynamic nodes {
    for_each = var.master_nodes
    content {
      internal_address = nodes.value.internal_address
      address = nodes.value.address
      user    = nodes.value.user
      role    = ["controlplane", "etcd"]
      ssh_key = file("${nodes.value.ssh_key}")
      labels  =  {"node_type" = "master"}
    }
  }

dynamic nodes {
    for_each = var.edge_nodes
    content {
      internal_address = nodes.value.internal_address
      address = nodes.value.address
      user    = nodes.value.user
      role    = ["worker"]
      ssh_key = file("${nodes.value.ssh_key}")
      labels  =  {"node_type" = "edge"}
    }
  }

dynamic nodes {
    for_each = var.service_nodes
    content {
      internal_address = nodes.value.internal_address
      address = nodes.value.address
      user    = nodes.value.user
      role    = ["worker"]
      ssh_key = file("${nodes.value.ssh_key}")
      labels  =  {"node_type" = "service"}
    }
  }

  authentication {
    strategy = "x509"
    sans     = flatten([var.kubeapi_sans_list])
  }

  bastion_host {
    address      = var.ssh_bastion_host
    user         = var.ssh_user
    ssh_key_path = var.ssh_key
    port         = 22
  }

  ingress {
    provider = "nginx"

    node_selector = {
      node_type = "edge"
    }
  }

  ignore_docker_version = var.ignore_docker_version
  kubernetes_version    = var.kubernetes_version

  # Workaround: make sure resources are created and deleted in the right order
  provisioner "local-exec" {
    command = "# ${join(",", var.rke_cluster_deps)}"
  }

  addons = <<EOL
---
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: cinder
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: kubernetes.io/cinder
reclaimPolicy: Delete
parameters:
  availability: nova
EOL

}

# Write YAML configs
locals {
  api_access = "https://${element(var.kubeapi_sans_list, 0)}:6443"
  api_access_regex = "/https://\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}:6443/"
}

resource "local_file" "kube_config_cluster" {
  count = var.write_kube_config_cluster ? 1 : 0
  filename = "${path.root}/kube_config_cluster.yml"

  # Workaround: https://github.com/rancher/rke/issues/705
  content = replace(
    rke_cluster.cluster.kube_config_yaml,
    local.api_access_regex,
    local.api_access,
  )
}

resource "local_file" "cluster_yml" {
  count = var.write_cluster_yaml ? 1 : 0
  filename = "${path.root}/cluster.yml"
  content = rke_cluster.cluster.rke_cluster_yaml
}

# Configure Kubernetes provider
provider "kubernetes" {
  host = local.api_access
  username = rke_cluster.cluster.kube_admin_user
  client_certificate = rke_cluster.cluster.client_cert
  client_key = rke_cluster.cluster.client_key
  cluster_ca_certificate = rke_cluster.cluster.ca_crt
}

resource "kubernetes_service_account" "tiller" {
  metadata {
    name = "terraform-tiller"
    namespace = "kube-system"
  }
}

resource "kubernetes_cluster_role_binding" "tiller" {
  depends_on = [kubernetes_service_account.tiller]
  metadata {
    name = "terraform-tiller"
  }

  role_ref {
    kind = "ClusterRole"
    name = "cluster-admin"
    api_group = "rbac.authorization.k8s.io"
  }

  subject {
    kind = "ServiceAccount"
    name = "terraform-tiller"
    api_group = ""
    namespace = "kube-system"
  }
}

