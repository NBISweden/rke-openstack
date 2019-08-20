variable "name_prefix" {
  description = "Prefix for the security group name"
}

variable "allowed_ingress_tcp" {
  type        = map(list(number))
  description = "Allowed TCP ingress traffic"
  default     = {}
}

variable "allowed_ingress_udp" {
  type        = map(list(number))
  description = "Allowed UDP ingress traffic"
  default     = {}
}

