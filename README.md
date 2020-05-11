# RKE deployment on Openstack using Terraform

This CLI allows you to install a Rancher Kubernetes Engine cluster of machines created with Terraform on Openstack. It provides automatic provisioning of `Cinder volumes` to Kubernetes pods and `nginx` as LoadBalancer.

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
pip install -r requirements.txt
pip install .
```
You can now explore the different functions provided by the CLI by executing:
```
rega --help
```

## Deployment configuration

The tool can use different configurations depending on your needs. The default
configuration lives in the https://github.com/NBISweden/rega-templates
repository so see that for more detailed information.

To create a new default deployment project you can run:
```
rega init <my-project>
cd <my-project>
```

And then confgiure that installation according to the underlying repos
documentation.

To use a custom deployment repository use the `-r`/`--repository` option to
the init command (possibly in conjunction with the `-b`/`--branch` option).

```
rega init --repository https://github.com/someorg/somerepo.git --branch stable <my-project>
cd <my-project>
```


## Quick start

### Firing up the infrastructure

To spawn the infrastructure execute the `apply` command.

```
rega apply
```

Once the deployment is done, you may explore the cluster:

```
rega kubectl get nodes -o wide
```


### Releasing resources

You can release the resources by running `destroy`:

```
rega destroy
```


## Detailed description

The rega tool looks for scripts in the scripts/ subdirectory of the template
repo that is instlled. These scripts have to follow the following naming
scheme in order for rega to find them and use them correctly (all other
shellscripts are ignored):

```
./scripts/<stage>_<type>_<name>.sh
```

Where `stage` is a number, `type` is any of `init`, `plan`, `apply`, and
`destroy` and `name` is a descriptive name of the script.

The rega tool then runs those scripts in the order specified by the `stage`
number when the commands `init`, `plan`, `apply` and `destroy` is used. The
expected behavior of scripts in the different stages are as follows:

### Stages

The stage specification is for specifying the order in which the modules
should run but also to group actions that belong together. For example with a
terraform stage you might have scripts to plan, apply and destroy that part of
the infrastructure and by naming them all with the same number. For example:

```
./scripts/03_plan_network.sh
./scripts/03_apply_network.sh
./scripts/03_destroy_network.sh
```

### Types

#### init

Run last in the `rega init` phase. This is where different initialisations can
take place. The most common here would be to download terraform modules into
the `./terraform_modules` directory for example.

Stages are run in order.

#### plan

Runs when the user enters `rega plan`. This is roughly equivalent to the
`terraform plan` command, so most of these will just execute a `terraform
plan` command or equivalent in whatever provisioner is used.

Stages are run in order.

#### apply

Runs when the user enters `rega apply`. This is for making changes to the
infrastructure. Recommended things to run in these stages are `terraform
apply` and `ansible-playbook` for example

Stages are run in order.

#### destroy

Runs when the user enters `rega destroy`. This should destroy the
infrastructure.

Stages are run in **reverse** order

### Run only a specific part of the available stages

It's possible to specify what stage to run to plan, apply and destroy by
adding the name of the module you want to run to the command line. For example the command:

```
rega apply network
```

would run all files that match the file pattern
`./scripts/[0-9]+_apply_network.sh` _in order_.

### Rancher Server

In order to manage the cluster from the Rancher UI, you can install `cert-manager` and the `Rancher server` using a Helm chart. After initialising Helm, you need to add the Helm chart repository that contains charts to install Rancher:

```
rega helm repo add rancher-stable https://releases.rancher.com/server-charts/stable
```

Rancher relies on cert-manager version v0.5.2 from the official charts repository. To install it use:
```
rega helm install cert-manager stable/cert-manager \
  --namespace kube-system \
  --version v0.5.2
```
And initialise the Rancher server by:
```
rega helm install rancher rancher-stable/rancher \
  --namespace cattle-system \
  --set hostname=ega.dash.<edge-ip>.nip.io
```

You can then visit the dashboard in the following address:
```https://ega.dash.<edge-ip>.nip.io```

