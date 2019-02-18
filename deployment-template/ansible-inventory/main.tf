variable cluster_prefix {}
variable ssh_user {}
variable kubernetes_version {}
variable docker_version {}

variable master_count {}

variable master_public_ip {
  type    = "list"
  default = [""]
}

variable master_private_ip {
  type    = "list"
  default = [""]
}

variable service_count {}

variable service_public_ip {
  type    = "list"
  default = [""]
}

variable service_private_ip {
  type    = "list"
  default = [""]
}

variable edge_count {}

variable edge_public_ip {
  type    = "list"
  default = [""]
}

variable edge_private_ip {
  type    = "list"
  default = [""]
}

variable inventory_template {}

variable inventory_output_file {
  default = "inventory"
}

locals {

  kubernetes_version = "${var.kubernetes_version}"
  docker_version = "${var.docker_version}"

  master_public_ip  = "${split(",", length(var.master_public_ip) == 0 ? join(",", list("")) : join(",", var.master_public_ip))}"
  master_private_ip = "${split(",", length(var.master_private_ip) == 0 ? join(",", list("")) : join(",", var.master_private_ip))}"

  service_public_ip  = "${split(",", length(var.service_public_ip) == 0 ? join(",", list("")) : join(",", var.service_public_ip))}"
  service_private_ip = "${split(",", length(var.service_private_ip) == 0 ? join(",", list("")) : join(",", var.service_private_ip))}"

  edge_public_ip  = "${split(",", length(var.edge_public_ip) == 0 ? join(",", list("")) : join(",", var.edge_public_ip))}"
  edge_private_ip = "${split(",", length(var.edge_private_ip) == 0 ? join(",", list("")) : join(",", var.edge_private_ip))}"

  # Format list of different service types
  masters    = "${join("\n",formatlist("ansible_host=%s ansible_user=%s private_ip=%s", local.master_public_ip, var.ssh_user, local.master_private_ip ))}"
}

# Generate inventory from template file
data "template_file" "inventory" {
  template = "${file("${path.root}/${ var.inventory_template }")}"

  vars {
    masters                = "${local.masters}"
    kubernetes_version     = "${local.kubernetes_version}"
    docker_version         = "${local.docker_version}"

  }
}