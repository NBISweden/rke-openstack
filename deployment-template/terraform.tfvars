## Cluster configuration ##
# Unique name for the resources
cluster_prefix="my-test"
# User for ssh connections. It varies among distributions. (CentOS might work with cloud-user or centos)
ssh_user="<ssh-user>"
# Network settings
external_network_id=""
floating_ip_pool=""
# Image name (RKE runs on almost any Linux OS)
image_name="<image-name>"
# Node counts and flavours (Note that these flavours are only indicative)
master_flavor_name="ssc.medium"
master_count=1
service_flavor_name="ssc.medium"
service_count=2
edge_flavor_name="ssc.medium"
edge_count=1
# Please check that the Kubernetes version is RKE 0.2.x compliant
kubernetes_version="v1.14.3-rancher1-1" 
