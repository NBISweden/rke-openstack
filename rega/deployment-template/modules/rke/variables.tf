variable "master_nodes" {
  description = "Master nodes info"
}

variable "service_nodes" {
  description = "Service nodes info"
}

variable "edge_nodes" {
  description = "Edge nodes info"
}

variable "ssh_bastion_host" {
  default = "Bastion SSH host"
}

variable "ssh_user" {
  description = "SSH user name"
}

variable "ssh_key" {
  description = "Path to private SSH key"
}

variable "kubeapi_sans_list" {
  type        = list(string)
  description = "SANS for the Kubernetes server API"
}

variable "ignore_docker_version" {
  description = "If true RKE won't check Docker version on images"
}

variable "kubernetes_version" {
  description = "Kubernetes version (should be RKE v0.1.x compliant)"
}

variable "write_kube_config_cluster" {
  description = "If true kube_config_cluster.yml will be written locally"
}

variable "write_cluster_yaml" {
  description = "If true cluster.yml will be written locally"
}

variable "os_username" {
  description = "Openstack user name"
}

variable "os_password" {
  description = "Openstack tenancy password"
}

variable "os_auth_url" {
  description = "Openstack auth url"
}

variable "os_project_id" {
  description = "Openstack tenant/project id"
}

variable "os_project_name" {
  description = "Openstack tenant/project name"
}

variable "os_user_domain_name" {
  description = "Openstack domain name"
}

