# REGA: RKE deployments using Terraform

This CLI allows you to install vanilla Kubernetes in a cluster of machines created with Terraform on Openstack. It also provides automatic provisioning of `Cinder volumes` to Kubernetes pods, `nginx` as LoadBalancer and the possibility to setup the `Rancher Server UI` to manage the cluster.

## Prerequisites
On your machine you need the following requirements:

- [Docker](https://www.docker.com/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
- [Helm](https://github.com/helm/helm/releases)
- [Python 3.5+](https://www.python.org/downloads/)
- Set up the environment by [sourcing the OpenStack RC](https://docs.openstack.org/zh_CN/user-guide/common/cli-set-environment-variables-using-openstack-rc.html) file for your project


## Installing the REGA client

In order to install the CLI please run:
```
python setup.py install
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
Once in your project folder, modify the file called `terraform.tfvars` where you specify the values for the following settings:

```yml
cluster_prefix="my-test"
ssh_key_pub="ssh_key.pub"
ssh_key="ssh_key"
external_network_id=""
floating_ip_pool=""
image_name="Ubuntu 16.04 LTS (Xenial Xerus) - latest"
master_flavor_name="ssc.medium"
master_count=1
service_flavor_name="ssc.medium"
service_count=2
edge_flavor_name="ssc.medium"
edge_count=1
# Openstack credentials for provisioning Cinder volumes
os_username=""
os_password=""
os_auth_url=""
os_tenant_id=""
os_tenant_name=""
os_domain_name=""
```

Once the deployment is done, you can configure `kubectl` and explore the cluster:

```
export KUBECONFIG="$PWD/kube_config_cluster.yml"
kubectl get nodes
```

## Release resources

You can release the resources by running:

```
rega destroy
```

## Rancher Server

In order to manage the cluster from the Rancher UI, you can install `cert-manager` and the `Rancher server` using a Helm chart. First use `helm repo add` command to add the Helm chart repository that contains charts to install Rancher:

```
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
