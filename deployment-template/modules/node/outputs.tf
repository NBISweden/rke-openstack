output "node_mappings" {
  description = "RKE node mappings"
  value       = ["${data.rke_node_parameter.node_mappings.*.json}"]
}

output "public_ip_list" {
  description = "List of floating IP addresses"
  value       = ["${openstack_compute_floatingip_v2.floating_ip.*.address}"]
}

output "access_ip_list" {
  description = "IP addresses for Ansible inventory"
  value = "${local.address_list}"
}

output "private_ip_list" {
  description = "List of local IP addresses"
  value = ["${openstack_compute_instance_v2.instance.*.network.0.fixed_ip_v4}"]
}

output "associate_floating_ip_id_list" {
  description = "Associate floating IP resource ID list"
  value       = ["${openstack_compute_floatingip_associate_v2.associate_floating_ip.*.id}"]
}

output "hostnames" {
  value = ["${openstack_compute_instance_v2.instance.*.name}"]
}
