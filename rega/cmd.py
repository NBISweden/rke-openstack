import sys
import os
import logging
from glob import glob
import re

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


class TemplateScripts:
    def __init__(self):
        self._scripts = self._find_scripts()


    def _find_scripts(self):
        scripts = []
        for script in glob('scripts/*.sh'):
            m = re.search('(\d+)_([^_]+)_(.*)\.sh', script)
            if m is None:
                continue
            scripts.append({
                'stage': int(m[1]),
                'type': m[2],
                'name': m[3],
                'path': script
            })
        scripts.sort(key=lambda x: x['stage'])
        return scripts


    def get_type(self, type):
        for script in self._scripts:
            if script['type'] == type:
                yield script


    def number_of_stages(self):
        return max( map( lambda x: x['stage'], self._scripts ) )


    def get_stage(self, n):
        for script in self._scripts:
            if script['stage'] == n:
                yield script


@click.group()
@click.option('-I', '--image', default=DOCKER_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def main(image):
    """REGA is a tool for provisioning RKE clusters."""
    # Dont check environment in case we are in init
    context = click.get_current_context()
    if context.invoked_subcommand != 'init':
        check_version(PACKAGE_VERSION)
        check_environment()

    global DOCKER_IMAGE
    DOCKER_IMAGE = image


@main.command('init')
@click.option('-r', '--repository', default='https://github.com/NBISweden/rega-templates.git',
              help="Specify the repo to use as a template for the infrastructure")
@click.option('-b', '--branch', default=f"master",
              help=f"The branch to checkout from the repo, default is master")
@click.argument('directory')
def init(repository, branch, directory):
    """Initialise a new REGA environment."""
    logging.info("""Initilising a new environment in %s""", directory)
    clone_deployment_templates(repository, branch, directory)
    generate_ssh_keys(directory)
    write_version_file(directory)

    run_init_scripts(directory)
    logging.info("""Environment initialised. Navigate to the %s folder and update the terraform.tfvars file with your configuration""", directory)


@main.command('version')
def version():
    """Output the version of the target provisioning container along with the original and current package versions."""
    try:
        with open('.version', 'r') as version_file:
            env_package = version_file.readline()
    except FileNotFoundError:
        sys.stderr.write("### ERROR ### The version file of the environment was not found.\n")
        sys.exit(1)

    t = PrettyTable(['Original package version', 'Current package version', 'Image version'])
    t.add_row([env_package, PACKAGE_VERSION, DOCKER_IMAGE])
    print(t)


@main.command('plan')
@click.argument('modules', nargs=-1)
def plan(modules):
    """Create a Terraform execution plan with the necessary actions to achieve the desired state."""
    logging.info("""Creating execution plan for %s module(s)""", ", ".join(modules))
    run_scripts(type='plan', selection=modules)


@main.command('apply')
@click.argument('modules', nargs=-1)
def apply(modules):
    """Apply the Terraform plan to spawn the desired resources."""
    logging.info("""Applying setup using modules %s""", ", ".join(modules))
    run_scripts(type='apply', selection=modules)


@main.command('destroy')
def destroy():
    """Releases the previously requested resources."""
    logging.info("""Destroying the infrastructure...""")
    run_scripts(type='destroy', selection=None)


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
    run_in_container([f'helm {extra_args}'])


@main.command('kubectl', context_settings={"ignore_unknown_options": True})
@click.argument('extra_args', nargs=-1, type=click.UNPROCESSED, callback=_fix_extra_args)
def kubectl(extra_args):
    """Execute the kubectl command in the provisioner container with the provided args."""
    logging.info("""Running kubectl with arguments: %s""", extra_args)
    run_in_container([f'kubectl {extra_args}'])


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


def run_in_container(commands):
    """Execute a sequence of shell commands in a Docker container."""
    logging.debug(f"Run in container: {commands}")

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
        entrypoint=['ash', '-c'],
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


def run_scripts(type, selection=None):
    scripts = TemplateScripts()
    for script in scripts.get_type(type):
        if selection and script['name'] not in selection:
            continue
        run_in_container([script['path']])


def run_init_scripts(directory):
    os.chdir(directory)
    run_scripts('init')


def clone_deployment_templates(repository, branch, directory):
    """Clone deployment template repo into new directory"""
    run_in_container([f'git clone --branch={branch} {repository} {directory}'])


def generate_ssh_keys(directory):
    """Create ssh keys for deployment"""

    if not os.path.isfile(directory + '/ssh_key.pub'):
        pu, pv = create_key_pair()
        with open(directory + '/ssh_key.pub', 'w') as key:
            key.write(pu)
        with open(directory + '/ssh_key', 'w') as key:
            key.write(pv)
            os.chmod(directory + '/ssh_key', 0o400)


def write_version_file(directory):
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


def check_version(target_package):
    """Check whether the version used to initiate the current deployment is the same as the installed one."""
    logging.debug(f"Checking whether version is {target_package}")
    try:
        with open('.version', 'r') as version_file:
            env_package = version_file.readline()
    except FileNotFoundError:
        sys.stderr.write("### ERROR ### The version file of the environment was not found.\n")
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
