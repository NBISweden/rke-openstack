output "secgroup_name" {
  description = "Name of the security group"
  value       = openstack_networking_secgroup_v2.secgroup.name
}

output "rule_id_list" {
  description = "Security rule resource ID list"
  value       = flatten([concat(openstack_networking_secgroup_rule_v2.ingress_tcp.*.id, openstack_networking_secgroup_rule_v2.ingress_udp.*.id)])
}

