resource "random_id" "suffix" {
  byte_length = 12
}

resource "openstack_compute_keypair_v2" "main" {
  name       = "${var.key_prefix}-keypair-${random_id.suffix.hex}"
  public_key = file(var.public_ssh_key)
}

