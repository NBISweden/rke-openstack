variable "node_count" {
  description = "Number of nodes to be created"
}

variable "name_prefix" {
  description = "Prefix for the node name"
}

variable "flavor_name" {
  description = "Flavor to be used for this node"
}

variable "image_name" {
  description = "Image to boot this node from"
}

variable "cloud_init_data" {
  description = "cloud-init data to pass onto all instances"
}

variable "ssh_user" {
  description = "SSH user name"
}

variable "ssh_key" {
  description = "Path to private SSH key"
}

variable "os_ssh_keypair" {
  description = "SSH keypair to inject in the instance (previosly created in OpenStack)"
}

variable "network_name" {
  description = "Name of the network to attach this node to"
}

variable "secgroup_name" {
  description = "Name of the security group for this node"
}

variable "assign_floating_ip" {
  description = "If true a floating IP will be attached to this node"
  default     = false
}

variable "floating_ip_pool" {
  description = "Name of the floating IP pool (don't leave it empty if assign_floating_ip is true)"
  default     = ""
}

variable "ssh_bastion_host" {
  description = "Bastion SSH host (mandatory if assign_floating_ip is false)"
  default     = ""
}

