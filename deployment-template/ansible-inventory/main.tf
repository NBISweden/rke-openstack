variable ssh_user {}
variable cluster_prefix {}

variable master_count {}

variable master_hostnames {
  type    = "list"
  default = [""]
}

variable master_public_ip {
  type    = "list"
  default = [""]
}

variable master_private_ip {
  type    = "list"
  default = [""]
}

variable service_count {}

variable service_hostnames {
  type    = "list"
  default = [""]
}

variable service_public_ip {
  type    = "list"
  default = [""]
}

variable service_private_ip {
  type    = "list"
  default = [""]
}

variable edge_count {}

variable edge_hostnames {
  type    = "list"
  default = [""]
}

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

  master_hostnames  = "${split(",", length(var.master_hostnames) == 0 ? join(",", list("")) : join(",", var.master_hostnames))}"
  master_private_ip = "${split(",", length(var.master_private_ip) == 0 ? join(",", list("")) : join(",", var.master_private_ip))}"

  edge_hostnames  = "${split(",", length(var.edge_hostnames) == 0 ? join(",", list("")) : join(",", var.edge_hostnames))}"
  edge_private_ip = "${split(",", length(var.edge_private_ip) == 0 ? join(",", list("")) : join(",", var.edge_private_ip))}"

  service_hostnames  = "${split(",", length(var.service_hostnames) == 0 ? join(",", list("")) : join(",", var.service_hostnames))}"
  service_private_ip = "${split(",", length(var.service_private_ip) == 0 ? join(",", list("")) : join(",", var.service_private_ip))}"

  masters    = "${join("\n",formatlist("%s ansible_host=%s ansible_user=%s private_ip=%s", local.master_hostnames, var.master_public_ip, var.ssh_user, local.master_private_ip ))}"
  edges    = "${join("\n",formatlist("%s ansible_host=%s ansible_user=%s private_ip=%s", local.edge_hostnames, var.edge_public_ip, var.ssh_user, local.edge_private_ip ))}"
  services    = "${join("\n",formatlist("%s ansible_host=%s ansible_user=%s private_ip=%s", local.service_hostnames, var.service_public_ip, var.ssh_user, local.service_private_ip ))}"
}

# Generate inventory from template file
data "template_file" "inventory" {
  template = "${file("${path.root}/${ var.inventory_template }")}"

  vars {
    masters                = "${local.masters}"
    edges                  = "${local.edges}"
    services               = "${local.services}"
  }
}

# Write the template to a file
resource "null_resource" "local" {
  # Trigger rewrite of inventory, uuid() generates a random string everytime it is called
  triggers {
    uuid = "${uuid()}"
  }

  triggers {
    template = "${data.template_file.inventory.rendered}"
  }

  provisioner "local-exec" {
    command = "echo \"${data.template_file.inventory.rendered}\" > \"${path.root}/${var.inventory_output_file}\""
  }
}
