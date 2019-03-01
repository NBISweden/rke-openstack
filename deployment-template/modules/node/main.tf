# Create instance
resource "openstack_compute_instance_v2" "instance" {
  count       = "${var.count}"
  name        = "${var.name_prefix}-${format("%03d", count.index)}"
  image_name  = "${var.image_name}"
  flavor_name = "${var.flavor_name}"
  key_pair    = "${var.os_ssh_keypair}"

  network {
    name = "${var.network_name}"
  }

  user_data = "${data.template_file.cloud_init.rendered}"

  config_drive = "true"

  security_groups = ["${var.secgroup_name}"]

  # Try to drain and delete node before downscaling
  provisioner "local-exec" {
    when       = "destroy"
    on_failure = "continue" # when running terraform destroy this provisioner will fail

    environment {
      KUBECONFIG = "./kube_config_cluster.yml"
    }

    command = "kubectl drain ${var.name_prefix}-${format("%03d", count.index)} --delete-local-data --force --ignore-daemonsets && kubectl delete node ${var.name_prefix}-${format("%03d", count.index)}"
  }
}

# Allocate floating IPs (if required)
resource "openstack_compute_floatingip_v2" "floating_ip" {
  count = "${var.assign_floating_ip ? var.count : 0}"
  pool  = "${var.floating_ip_pool}"
}

# Associate floating IPs (if required)
resource "openstack_compute_floatingip_associate_v2" "associate_floating_ip" {
  count       = "${var.assign_floating_ip ? var.count : 0}"
  floating_ip = "${element(openstack_compute_floatingip_v2.floating_ip.*.address, count.index)}"
  instance_id = "${element(openstack_compute_instance_v2.instance.*.id, count.index)}"
}

locals {
  # Workaround for list not supported in conditionals (https://github.com/hashicorp/terraform/issues/12453)
  address_list = ["${split(",", var.assign_floating_ip ? join(",", openstack_compute_floatingip_v2.floating_ip.*.address) : join(",", openstack_compute_instance_v2.instance.*.network.0.fixed_ip_v4))}"]
}

data template_file "cloud_init" {
  template = "${file("${path.module}/${var.cloud_init_data}")}"

  vars {
    boot_console = "centos",
    device_path = "/dev/vda"
  }
}

data rke_node_parameter "node_mappings" {
  count = "${var.count}"

  address           = "${element(local.address_list, count.index)}"
  user              = "${var.ssh_user}"
  ssh_key_path      = "${var.ssh_key}"
  internal_address  = "${element(openstack_compute_instance_v2.instance.*.network.0.fixed_ip_v4, count.index)}"
  hostname_override = "${element(openstack_compute_instance_v2.instance.*.name, count.index)}"
  role              = "${var.role}"
  labels            = "${var.labels}"
}
