resource "openstack_networking_secgroup_v2" "secgroup" {
  name        = "${var.name_prefix}-secgroup"
  description = "Security group for RKE"
}

resource "openstack_networking_secgroup_rule_v2" "internal_tcp" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = "1"
  port_range_max    = "64535"
  remote_group_id   = openstack_networking_secgroup_v2.secgroup.id
  security_group_id = openstack_networking_secgroup_v2.secgroup.id
}

resource "openstack_networking_secgroup_rule_v2" "internal_udp" {
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "udp"
  port_range_min    = "1"
  port_range_max    = "64535"
  remote_group_id   = openstack_networking_secgroup_v2.secgroup.id
  security_group_id = openstack_networking_secgroup_v2.secgroup.id
}

locals {
  expanded_tcp_ingresses = flatten([
    for ip, ports in var.allowed_ingress_tcp:
      [for port in ports: {"ip" = ip, "port" = port}]
  ])
  expanded_udp_ingresses = flatten([
    for ip, ports in var.allowed_ingress_udp:
      [for port in ports: {"ip" = ip, "port" = port}]
  ])
}

resource "openstack_networking_secgroup_rule_v2" "ingress_tcp" {
  count = length(local.expanded_tcp_ingresses)

  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  remote_ip_prefix  = local.expanded_tcp_ingresses[count.index]["ip"]
  port_range_min    = local.expanded_tcp_ingresses[count.index]["port"]
  port_range_max    = local.expanded_tcp_ingresses[count.index]["port"]
  security_group_id = openstack_networking_secgroup_v2.secgroup.id
}

resource "openstack_networking_secgroup_rule_v2" "ingress_udp" {
  count = length(local.expanded_udp_ingresses)

  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "udp"
  remote_ip_prefix  = local.expanded_udp_ingresses[count.index]["ip"]
  port_range_min    = local.expanded_udp_ingresses[count.index]["port"]
  port_range_max    = local.expanded_udp_ingresses[count.index]["port"]
  security_group_id = openstack_networking_secgroup_v2.secgroup.id
}

