variable ssh_user {}
variable cluster_prefix {}

variable master_count {}

variable master_hostnames {
  type    = list(string)
  default = [""]
}

variable master_public_ip {
  type    = list(string)
  default = [""]
}

variable master_private_ip {
  type    = list(string)
  default = [""]
}

variable service_count {}

variable service_hostnames {
  type    = list(string)
  default = [""]
}

variable service_public_ip {
  type    = list(string)
  default = [""]
}

variable service_private_ip {
  type    = list(string)
  default = [""]
}

variable edge_count {}

variable edge_hostnames {
  type    = list(string)
  default = [""]
}

variable edge_public_ip {
  type    = list(string)
  default = [""]
}

variable edge_private_ip {
  type    = list(string)
  default = [""]
}

variable inventory_template {}

variable inventory_output_file {
  default = "inventory"
}

locals {

  master_hostnames  = split(",", length(var.master_hostnames) == 0 ? join(",", list("")) : join(",", slice(var.master_hostnames, 0, var.master_count)))
  master_private_ip = split(",", length(var.master_private_ip) == 0 ? join(",", list("")) : join(",", slice(var.master_private_ip, 0, var.master_count)))

  edge_hostnames  = split(",", length(var.edge_hostnames) == 0 ? join(",", list("")) : join(",", slice(var.edge_hostnames, 0, var.edge_count)))
  edge_private_ip = split(",", length(var.edge_private_ip) == 0 ? join(",", list("")) : join(",", slice(var.edge_private_ip, 0, var.edge_count)))

  service_hostnames  = split(",", length(var.service_hostnames) == 0 ? join(",", list("")) : join(",", slice(var.service_hostnames, 0, var.service_count)))
  service_private_ip = split(",", length(var.service_private_ip) == 0 ? join(",", list("")) : join(",", slice(var.service_private_ip, 0, var.service_count)))

  masters  = join("\n",formatlist("%s ansible_host=%s ansible_user=%s private_ip=%s", local.master_hostnames,  slice(var.master_public_ip,  0, var.master_count),  var.ssh_user, local.master_private_ip  ))
  edges    = join("\n",formatlist("%s ansible_host=%s ansible_user=%s private_ip=%s", local.edge_hostnames,    slice(var.edge_public_ip,    0, var.edge_count),    var.ssh_user, local.edge_private_ip    ))
  services = join("\n",formatlist("%s ansible_host=%s ansible_user=%s private_ip=%s", local.service_hostnames, slice(var.service_public_ip, 0, var.service_count), var.ssh_user, local.service_private_ip ))
}

# Generate inventory from template file
data "template_file" "inventory" {
  template = "${file("${path.root}/${ var.inventory_template }")}"

  vars = {
    masters                = local.masters
    edges                  = local.edges
    services               = local.services
  }
}

# Write the template to a file
resource "null_resource" "local" {
  # Trigger rewrite of inventory, uuid() generates a random string everytime it is called
  triggers = {
    uuid = uuid()
    template = data.template_file.inventory.rendered
}
  provisioner "local-exec" {
    command = "echo \"${data.template_file.inventory.rendered}\" > \"${path.root}/${var.inventory_output_file}\""
  }
}
