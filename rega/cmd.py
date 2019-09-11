import sys
import os
import logging

import yaml
import hcl
import click
import docker
import pkg_resources
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from prettytable import PrettyTable

logging.basicConfig(level=logging.INFO)
PACKAGE_VERSION = pkg_resources.get_distribution("rega").version
DOCKER_IMAGE = f'nbisweden/rega:release-v{PACKAGE_VERSION}'


@click.group()
@click.option('-I', '--image', default=DOCKER_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def main(image):
    """REGA is a tool for provisioning RKE clusters."""
    global DOCKER_IMAGE
    DOCKER_IMAGE = image


@main.command('init')
@click.option('-r', '--repository', default='https://github.com/NBISweden/rega-templates.git',
              help="Specify the repo to use as a template for the infrastructure")
@click.option('-b', '--branch', default=f"v{PACKAGE_VERSION}",
              help=f"The branch to checkout from the repo, default is v{PACKAGE_VERSION}")
@click.argument('directory')
def init(repository, branch, directory):
    """Initialise a new REGA environment."""
    logging.info("""Initilising a new environment in %s""", directory)
    create_deployment(repository, branch, directory)
    logging.info("""Environment initialised. Navigate to the %s folder and update the terraform.tfvars file with your configuration""", directory)


@main.command('version')
def version():
    """Output the version of the target provisioning container along with the original and current package versions."""
    try:
        with open('.version', 'r') as version_file:
            env_package = version_file.readline()
    except FileNotFoundError:
        sys.stderr.write("### ERROR ### The version file of the environment was not found.")
        sys.exit(1)

    t = PrettyTable(['Original package version', 'Current package version', 'Image version'])
    t.add_row([env_package, PACKAGE_VERSION, DOCKER_IMAGE])
    print(t)


@main.command('plan')
@click.option('-M', '--modules', default='all',
              type=click.Choice(['infra', 'all']),
              help='Options are: "infra" and "all"')
@click.option('-C', '--config', default="backend.cfg",
              help='File used to define backend config')
def plan(modules, config):
    """Create a Terraform execution plan with the necessary actions to achieve the desired state."""
    logging.info("""Creating execution plan for %s modules""", modules)
    terraform_plan(modules, config)


@main.command('apply')
@click.option('-M', '--modules', default='all',
              type=click.Choice(['infra', 'all']),
              help='Options are: "infra" and "all"')
@click.option('-C', '--config', default="backend.cfg",
              help='File used to define backend config')
def apply(modules, config):
    """Apply the Terraform plan to spawn the desired resources."""
    logging.info("""Applying setup using mode %s""", modules)
    apply_tf_modules(modules, config)


@main.command('destroy')
def destroy():
    """Releases the previously requested resources."""
    logging.info("""Destroying the infrastructure...""")

    # In order for the destruction to work on all our infrastructures we need to
    # run the different modules separately to avoid terraform hanging while
    # interacting with the openstack api.
    terraform_destroy(get_tf_modules('k8s'))
    terraform_destroy(get_tf_modules('infra'))
    terraform_destroy(get_tf_modules('network'))
    terraform_destroy(get_tf_modules('secgroup'), parallelism=1)


def _fix_extra_args(ctx, param, value):
    """Use together with click.argument to convert tuple to string."""
    return " ".join(value)


@main.command('terraform', context_settings={"ignore_unknown_options": True})
@click.argument('extra_args', nargs=-1, type=click.UNPROCESSED, callback=_fix_extra_args)
def terraform(extra_args):
    """Execute the terraform command in the provisioner container with the provided args."""
    logging.info("""Running terraform with arguments: %s""", extra_args)
    run_in_container([f'terraform {extra_args}'])


@main.command('openstack', context_settings={"ignore_unknown_options": True})
@click.argument('extra_args', nargs=-1, type=click.UNPROCESSED, callback=_fix_extra_args)
def openstack(extra_args):
    """Execute the openstack command in the provisioner container with the provided args."""
    logging.info("""Running openstack with arguments: %s""", extra_args)
    run_in_container(['openstack {}'.format(extra_args)])


@main.command('helm', context_settings={"ignore_unknown_options": True})
@click.argument('extra_args', nargs=-1, type=click.UNPROCESSED, callback=_fix_extra_args)
def helm(extra_args):
    """Execute the helm command in the provisioner container with the provided args."""
    logging.info("""Running helm with arguments: %s""", extra_args)
    check_version(PACKAGE_VERSION)
    run_in_container([f'helm {extra_args}'])


@main.command('kubectl', context_settings={"ignore_unknown_options": True})
@click.argument('extra_args', nargs=-1, type=click.UNPROCESSED, callback=_fix_extra_args)
def kubectl(extra_args):
    """Execute the kubectl command in the provisioner container with the provided args."""
    logging.info("""Running kubectl with arguments: %s""", extra_args)
    check_version(PACKAGE_VERSION)
    run_in_container([f'kubectl {extra_args}'])


@main.command('provision')
@click.argument('playbook')
def provision(playbook):
    """Execute the Ansible playbook specified as an argument."""
    generate_vars_file()
    run_ansible(playbook)


def download_image(client):
    """Attempt to download the target Docker image."""
    try:
        client.images.get(DOCKER_IMAGE)
    except docker.errors.ImageNotFound:
        logging.info("""Image %s not present locally, trying to pull...""", DOCKER_IMAGE)
        try:
            client.images.pull(DOCKER_IMAGE)
        except docker.errors.APIError:
            sys.stderr.write("### ERROR ### Unable to pull the image {}. Does it exist?\n".format(DOCKER_IMAGE))
            sys.exit(1)


def run_in_container(commands, check_version=True):
    """Execute a sequence of shell commands in a Docker container."""
    logging.debug(f"Run in container: {commands}")
    if check_version:
        check_version(PACKAGE_VERSION)
    check_environment()

    logging.debug(f"Run in container: -> Initialising docker client")
    client = docker.from_env()
    download_image(client)
    env = list(filter_vars(os.environ))
    volume_mount = {os.getcwd(): {'bind': '/mnt/deployment/', 'mode': 'rw'}}
    container_wd = '/mnt/deployment/'

    assert isinstance(commands, list)

    logging.debug(f"Run in container: -> setting up environment")
    if os.path.isfile('./kube_config_cluster.yml'):
        env.append('KUBECONFIG=/mnt/deployment/kube_config_cluster.yml')
    env.append('HELM_HOME=/mnt/deployment/.helm')

    commands_as_string = " && ".join(commands)
    logging.debug(f"Run in container: -> Starting the command")
    runner = client.containers.run(
        DOCKER_IMAGE,
        volumes=volume_mount,
        environment=env,
        working_dir=container_wd,
        entrypoint=['bash', '-c'],
        command=f'"{commands_as_string}"',
        detach=True
    )

    logging.debug(f"Run in container: -> Reading stdout from command")
    for line in runner.logs(stream=True, follow=True):
        # No need to add newlines since line already has them, so end="".
        print(line.decode(), end="")

    logging.debug(f"Run in container: -> Waiting for command to finish")
    result = runner.wait()
    exit_code = result.get('StatusCode', 1)
    runner.remove()

    return exit_code


def apply_tf_modules(target, config):
    """Apply the correct target to run Terraform."""
    if target == 'infra':
        terraform_apply(get_tf_modules('network'), config)
        terraform_apply(get_tf_modules('secgroup'), config, parallelism=1)
        terraform_apply(get_tf_modules('infra'), config)
    elif target == 'all':
        network_exit_code = terraform_apply(get_tf_modules('network'), config)
        secgroup_exit_code = terraform_apply(get_tf_modules('secgroup'), config, parallelism=1)
        infra_exit_code = terraform_apply(get_tf_modules('infra'), config)
        if infra_exit_code == 0 and secgroup_exit_code == 0 and network_exit_code == 0:
            generate_vars_file()
            ansible_exit_code = run_ansible('setup.yml')
            if ansible_exit_code == 0:
                terraform_apply(get_tf_modules('k8s'), config)


def get_tf_modules(target):
    """Retrieve the target modules to run Terraform."""
    logging.debug(f"Get tf modules: {target}")
    infra_modules = '-target=module.master\
                    -target=module.service -target=module.edge\
                    -target=module.inventory -target=module.keypair'
    k8s_modules = '-target=module.rke'
    secgroup_modules = '-target=module.secgroup'
    network_modules = '-target=module.network'

    if target == 'infra':
        return infra_modules
    if target == 'k8s':
        return k8s_modules
    if target == 'secgroup':
        return secgroup_modules
    if target == 'network':
        return network_modules
    return ''


def terraform_plan(target, config):
    """Execute Terraform plan."""
    return run_in_container(['terraform init -backend-config={} -plugin-dir=/terraform_plugins'.format(config),
                             'terraform plan {}'.format(get_tf_modules(target))])


def terraform_apply(modules, config, parallelism=10):
    """Execute Terraform apply."""
    return run_in_container(['terraform init -backend-config={} -plugin-dir=/terraform_plugins'.format(config),
                             'terraform apply -parallelism={} -auto-approve {}'.format(parallelism, modules)])


def terraform_destroy(modules, parallelism=10):
    """Execute Terraform destroy."""
    run_in_container(['terraform destroy -parallelism={} -force {}'.format(parallelism, modules)])


def run_ansible(playbook):
    """Run a given ansible playbook."""
    return run_in_container(['ansible-playbook playbooks/{}'.format(playbook)])


def create_deployment(repository, branch, directory):
    """Copy relevant files to new folder."""

    run_in_container([f'git clone --branch={branch} {repository} {directory}'], check_version=False)

    if not os.path.isfile(directory + '/ssh_key.pub'):
        pu, pv = create_key_pair()
        with open(directory + '/ssh_key.pub', 'w') as key:
            key.write(pu)
        with open(directory + '/ssh_key', 'w') as key:
            key.write(pv)
            os.chmod(directory + '/ssh_key', 0o400)

    with open(directory + '/.version', 'w') as version_file:
        version_file.write(pkg_resources.get_distribution("rega").version)


def check_environment():
    """Check if env is ready to proceed."""
    logging.debug(f"Checking that evnironment is ok")
    if not os.environ.get('OS_AUTH_URL', False):
        sys.stderr.write("### ERROR ### You need to source the openstack credentials file\n")
        sys.exit(1)

    if not os.path.isfile('terraform.tfvars'):
        sys.stderr.write("### ERROR ### terraform.tfvars not found. Please check you are in your environment folder\n")
        sys.exit(1)


def deployment_template_dir():
    """Get the directory of the deployment template."""
    return pkg_resources.resource_filename(__name__, "deployment-template")


def check_version(target_package):
    """Check whether the version used to initiate the current deployment is the same as the installed one."""
    logging.debug(f"Checking whether version is {target_package}")
    try:
        with open('.version', 'r') as version_file:
            env_package = version_file.readline()
    except FileNotFoundError:
        sys.stderr.write("### ERROR ### The version file of the environment was not found.")
        sys.exit(1)

    t = PrettyTable(['Original', 'Current'])
    t.add_row([env_package, target_package])

    if env_package != target_package:
        sys.stderr.write("### WARNING ### The rega environment was created with a different package version\n")
        print(t)


def create_key_pair():
    """Create a RSA key pair."""
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=4096
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.TraditionalOpenSSL,
        crypto_serialization.NoEncryption())
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH,
        crypto_serialization.PublicFormat.OpenSSH
    )
    return (public_key.decode('utf-8'), private_key.decode('utf-8'))


def generate_vars_file():
    """Generate Ansible vars file."""
    tf_default_vars = dict()
    tf_vars = dict()

    with open("variables.tf", 'r') as stream:
        tf_default_vars = hcl.load(stream)

    ssh_user = tf_default_vars['variable']['ssh_user']['default']
    private_key = tf_default_vars['variable']['ssh_key']['default']
    cluster_prefix = tf_default_vars['variable']['cluster_prefix']['default']

    with open("terraform.tfvars", 'r') as stream:
        tf_vars = hcl.load(stream)

    if 'cluster_prefix' in tf_vars:
        cluster_prefix = tf_vars['cluster_prefix']
    if 'ssh_key' in tf_vars:
        private_key = tf_vars['ssh_key']
    if 'ssh_user' in tf_vars:
        ssh_user = tf_vars['ssh_user']

    data = {
        "edge_host": "{}-edge-000".format(cluster_prefix),
        "edge_ip": "{{ hostvars.get(edge_host)[\"ansible_host\"] }}",
        "ssh_user": ssh_user,
        "private_key": private_key
    }

    vars_file = 'playbooks/group_vars/all'

    with open(vars_file, 'w') as fh:
        fh.write(yaml.dump(data, default_flow_style=False))


def filter_vars(seq):
    """Retrieve OS and TF specific env vars."""
    for key, val in seq.items():
        if key.startswith('TF_'):
            yield key + '=' + val
        elif key.startswith('OS_'):
            yield key + '=' + val
            yield 'TF_VAR_' + key.lower() + '=' + val


if __name__ == '__main__':
    main()
