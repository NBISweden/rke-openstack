# REGA: RKE deployments using Terraform

This CLI allows you to install vanilla Kubernetes in a cluster of machines created with Terraform on Openstack. It also provides automatic provisioning of `Cinder volumes` to Kubernetes pods, `nginx` as LoadBalancer and the possibility to setup the `Rancher Server UI` to manage the cluster.

## Prerequisites
On your machine you need the following requirements:

- [Docker](https://www.docker.com/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [Helm](https://github.com/helm/helm/releases)
- [Python 3.7+](https://www.python.org/downloads/)
- Set up the environment by [sourcing the OpenStack RC](https://docs.openstack.org/zh_CN/user-guide/common/cli-set-environment-variables-using-openstack-rc.html) file for your project


## Installing the REGA client

In order to install the CLI please run:
```
make install
```
You can now explore the different functions provided by the CLI by executing:
```
rega --help
```

## Deployment

To create a new deployment project you can run:
```
rega init <my-project>
cd <my-project>
```
Once in your project folder, create a file called `terraform.tfvars` where you specify the values for the following settings:

```yml
# Unique name for the resources
cluster_prefix="my-test"
# Key pair settings
ssh_key_pub="ssh_key.pub"
ssh_key="ssh_key"
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
```

To fire up the infrastructure execute the `apply` command with the desired modules. By default all modules will be created.
```
rega apply --modules=[infra,k8s,all]
```

Once the deployment is done, you can configure `kubectl` and explore the cluster:

```
export KUBECONFIG="$PWD/kube_config_cluster.yml"
kubectl get nodes
```


## Provisioning with Ansible

You can run Ansible playbooks against the virtual machines by running the `provision` command. It expects the path of the playbook under the `playbooks` folder. For example:

```
rega provision setup
```

## Releasing resources

You can release the resources by running `destroy` with the desired modules. By default all modules will be deleted.

```
rega destroy --modules=[infra,k8s,all]
```

## Rancher Server

In order to manage the cluster from the Rancher UI, you can install `cert-manager` and the `Rancher server` using a Helm chart. After initialising Helm, you need to add the Helm chart repository that contains charts to install Rancher:

```
helm init --service-account terraform-tiller
helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
```

Rancher relies on cert-manager version v0.5.2 from the official charts repository. To install it use:
```
helm install stable/cert-manager \
  --name cert-manager \
  --namespace kube-system \
  --version v0.5.2
```
And initialise the Rancher server by:
```
helm install rancher-stable/rancher \
  --name rancher \
  --namespace cattle-system \
  --set hostname=ega.dash.<edge-ip>.nip.io
```

You can then visit the dashboard in the following address:
```https://ega.dash.<edge-ip>.nip.io```
