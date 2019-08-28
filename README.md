# RKE deployment on Openstack using Terraform

This CLI allows you to install vanilla Kubernetes in a cluster of machines created with Terraform on Openstack. It also provides automatic provisioning of `Cinder volumes` to Kubernetes pods, `nginx` as LoadBalancer and the possibility to setup the `Rancher Server UI` to manage the cluster.

## Prerequisites
On your machine you need the following requirements:

- [Docker](https://www.docker.com/)
- [Python 3.7+](https://www.python.org/downloads/)
- Set up the environment by [sourcing the OpenStack RC](https://docs.openstack.org/zh_CN/user-guide/common/cli-set-environment-variables-using-openstack-rc.html) file for your project

## Installing the CLI

You need `python3` installed. I recommend that you use `virtualenv` for installation of the CLI:

    virtualenv venv
    source venv/bin/activate

In order to install the CLI please run:
```
make install
```
You can now explore the different functions provided by the CLI by executing:
```
rega --help
```

## Deployment configuration

To create a new deployment project you can run:
```
rega init <my-project>
cd <my-project>
```
Once in your project folder, update the file called `terraform.tfvars` where you specify the values for the following settings:

```yml
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
# Please check that the Kubernetes version is RKE 0.2.x compliant)
kubernetes_version="v1.14.6-rancher1-1"

# Security groups
allowed_ingress_tcp={
  # These are the ports you need to work with kubernetes and rancher from your
  # machine.
  #"<YOUR CIDR>" = [22, 6443, 80, 443, 10250]
}
allowed_ingress_udp={}
secgroups = []
```

If you want the state to be stored into a S3 remote backend you can add the following configuration to the `backend.cfg` file:

```
access_key = "xyz"
secret_key = "xyz"
bucket = "bucketname"
region = "us-east-1"
endpoint = "https://s3.endpoint"
key = "terraform.tfstate"
skip_requesting_account_id = true
skip_credentials_validation = true
skip_get_ec2_platforms = true
skip_metadata_api_check = true
skip_region_validation = true
```

And for Swift:

```
container          = "cluster-state"
archive_container  = "cluster-state-archive"
```

## Firing up the infrastructure

To spawn the infrastructure execute the `apply` command with the desired modules. By default all modules will be created and we do not initialise Terraform to support a remote backend. With `--backend`it is possible to change the type of backend to use. The `--config` flag can be used to specify a custom file path for the backend configuration.

```
rega apply --modules=[infra,all] --backend=[local,s3,swift] [--config=<backend config file>]
```

Once the deployment is done, you may explore the cluster:

```
kubectl get nodes -o wide
```


## Provisioning with Ansible

You can run Ansible playbooks against the virtual machines by running the `provision` command. It expects the path of the playbook under the `playbooks` folder. For example:

```
rega provision setup.yml
```

## Releasing resources

You can release the resources by running `destroy` with the desired modules. By default all modules will be deleted.

```
rega destroy --modules=[infra,k8s,all]
```

## Starting Tiller

Prior to installing Helm charts, you need to have Tiller up and running in your cluster:

```
rega helm init --service-account terraform-tiller
```

## Rancher Server

In order to manage the cluster from the Rancher UI, you can install `cert-manager` and the `Rancher server` using a Helm chart. After initialising Helm, you need to add the Helm chart repository that contains charts to install Rancher:

```
rega helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
```

Rancher relies on cert-manager version v0.5.2 from the official charts repository. To install it use:
```
rega helm install stable/cert-manager \
  --name cert-manager \
  --namespace kube-system \
  --version v0.5.2
```
And initialise the Rancher server by:
```
rega helm install rancher-stable/rancher \
  --name rancher \
  --namespace cattle-system \
  --set hostname=ega.dash.<edge-ip>.nip.io
```

You can then visit the dashboard in the following address:
```https://ega.dash.<edge-ip>.nip.io```
