
import sys
import yaml
import hcl
import os
import click
import docker
import logging
import pkg_resources
from distutils import dir_util
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from jinja2 import Environment, FileSystemLoader
from prettytable import PrettyTable

logging.basicConfig(level=logging.INFO)
PACKAGE_VERSION = pkg_resources.get_distribution("rega").version
DEFAULT_IMAGE = f'nbisweden/rega:release-v{PACKAGE_VERSION}'


@click.group()
def main():
    """REGA is a tool for provisioning RKE clusters."""


@main.command('init')
@click.argument('directory')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def init(directory, image):
    """Initialises a new REGA environment."""
    logging.info("""Initilising a new environment in {}""".format(directory))
    client = docker.from_env()
    download_image(client, image)
    check_init_dir()
    create_deployment(directory)
    logging.info("""Environment initialised. Navigate to the {} folder and update the terraform.tfvars file with your configuration""".format(directory))


@main.command('version')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG')
def version(image):
    """Outputs the version of the target provisioning container along with the original and current package versions."""
    check_environment()

    with open('.version', 'r') as version_file:
        env_package = version_file.readline()

    t = PrettyTable(['Original package version', 'Current package version', 'Image version'])
    t.add_row([env_package, PACKAGE_VERSION, image])
    print(t)


@main.command('plan')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
@click.option('-M', '--modules', default='all',
              type=click.Choice(['infra', 'all']),
              help='Options are: "infra" and "all"')
@click.option('-B', '--backend', default='local',
              type=click.Choice(['local', 's3', 'swift']),
              help='Options are: "local", "s3" and "swift"')
@click.option('-C', '--config', default="backend.cfg",
              help='File used to define backend config')
def plan(image, modules, backend, config):
    """Creates a Terraform execution plan with the necessary actions to achieve the desired state."""
    logging.info("""Creating execution plan for {} modules""".format(modules))
    check_environment()
    check_version(PACKAGE_VERSION)
    terraform_plan(modules, image, backend, config)


@main.command('apply')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
@click.option('-M', '--modules', default='all',
              type=click.Choice(['infra', 'all']),
              help='Options are: "infra" and "all"')
@click.option('-B', '--backend', default='local',
              type=click.Choice(['local', 's3', 'swift']),
              help='Options are: "local", "s3" and "swift"')
@click.option('-C', '--config', default="backend.cfg",
              help='File used to define backend config')
def apply(image, modules, backend, config):
    """Applies the Terraform plan to spawn the desired resources."""
    logging.info("""Applying setup using mode {}""".format(modules))
    check_environment()
    check_version(PACKAGE_VERSION)
    apply_tf_modules(modules, image, backend, config)


@main.command('destroy')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
@click.option('-M', '--modules', default='all',
              type=click.Choice(['infra', 'k8s', 'all']),
              help='Options are: "infra", "k8s" and "all"')
def destroy(image, modules):
    """Releases the previously requested resources."""
    logging.info("""Destroying the infrastructure using mode {}""".format(modules))
    tf_modules = get_tf_modules(modules)
    check_environment()
    check_version(PACKAGE_VERSION)
    run_in_container(['terraform destroy -force {}'.format(tf_modules)], image)


@main.command('terraform')
@click.argument('extra_args')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def terraform(extra_args, image):
    """Executes the terraform command in the provisioner container with the provided args."""
    logging.info("""Running terraform with arguments: {}""".format(extra_args))
    check_environment()
    check_version(PACKAGE_VERSION)
    run_in_container(['terraform {}'.format(extra_args)], image)


@main.command('openstack')
@click.argument('extra_args')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def openstack(extra_args, image):
    """Executes the openstack command in the provisioner container with the provided args."""
    logging.info("""Running openstack with arguments: {}""".format(extra_args))
    check_environment()
    check_version(PACKAGE_VERSION)
    run_in_container(['openstack {}'.format(extra_args)], image)


@main.command('provision')
@click.argument('extra_args')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def provision(image, extra_args):
    """Executes the Ansible playbook specified as an argument."""
    check_environment()
    check_version(PACKAGE_VERSION)
    generate_vars_file()
    run_ansible(extra_args, image)


def download_image(client, image):
    """Attempts to download the target Docker image."""
    try:
        client.images.pull(image)
    except docker.errors.APIError:
        print("### ERROR ### Unable to pull the image {}. Does it exist?".format(image))
        sys.exit(1)


def run_in_container(commands, image):
    """Executes a sequence of shell commands in a Docker container."""
    client = docker.from_env()
    download_image(client, image)
    env = list(filter_vars(os.environ))
    volume_mount = {os.getcwd(): {'bind': '/mnt/deployment/', 'mode': 'rw'}}
    container_wd = '/mnt/deployment/'

    assert isinstance(commands, list)

    commands_as_string = " && ".join(commands)
    runner = client.containers.run(
        image,
        volumes=volume_mount,
        environment=env,
        working_dir=container_wd,
        entrypoint=['bash', '-c'],
        command=f'"{commands_as_string}"',
        detach=True
    )

    for line in runner.logs(stream=True, follow=True):
        print(line.decode())

    result = runner.wait()
    exit_code = result.get('StatusCode', 1)
    runner.remove()

    return exit_code


def render(template_path, data, extensions=None, strict=False):
    """Renders a jinja2 template."""
    if extensions is None:
        extensions = []
    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_path)),
        extensions=extensions,
        keep_trailing_newline=True,
    )
    if strict:
        from jinja2 import StrictUndefined
        env.undefined = StrictUndefined

    env.globals['environ'] = os.environ.get

    output = env.get_template(os.path.basename(template_path)).render(data)
    return output.encode('utf-8')


def apply_tf_modules(target, image, backend, config):
    """Applies the correct target to run Terraform."""
    if target == 'infra':
        terraform_apply(get_tf_modules(target), image, backend, config)
    elif target == 'all':
        infra_exit_code = terraform_apply(get_tf_modules('infra'), image, backend, config)
        if infra_exit_code == 0:
            generate_vars_file()
            ansible_exit_code = run_ansible('setup.yml', image)
            if ansible_exit_code == 0:
                terraform_apply(get_tf_modules('k8s'), image, backend, config)


def get_tf_modules(target):
    """Retrieves the target modules to run Terraform."""
    infra_modules = '-target=module.network -target=module.secgroup\
                    -target=module.master -target=module.service -target=module.edge\
                    -target=module.inventory -target=module.keypair'
    k8s_modules = '-target=module.rke'

    if target == 'infra':
        return infra_modules
    elif target == 'k8s':
        return k8s_modules
    elif target == 'all':
        return ''


def terraform_plan(target, image, backend, config):
    """Executes Terraform plan."""
    setup_tf_backend(backend)
    return run_in_container(['terraform init -backend-config={} -plugin-dir=/terraform_plugins'.format(config),
                             'terraform plan {}'.format(get_tf_modules(target))], image)


def terraform_apply(modules, image, backend, config):
    """Executes Terraform apply."""
    setup_tf_backend(backend)
    return run_in_container(['terraform init -backend-config={} -plugin-dir=/terraform_plugins'.format(config),
                             'terraform apply -auto-approve {}'.format(modules)], image)


def setup_tf_backend(backend):
    """Renders the main.tf file with the chosen backend type."""
    main_out = render('main.j2', {'backend_type': backend})
    main_out = main_out.decode('utf-8')
    main_file = open('main.tf', 'w')
    main_file.write(main_out)
    main_file.close()


def run_ansible(playbook, image):
    """Runs a given ansible playbook."""
    return run_in_container(['ansible-playbook playbooks/{}'.format(playbook)], image)


def create_deployment(directory):
    """Copies relevant files to new folder."""
    if os.path.exists('deployment-template'):
        dir_util.mkpath(directory)
        dir_util.copy_tree('deployment-template/', './{}/'.format(directory))
    else:
        sys.stderr.write("### ERROR ### deployment-template folder not found. Are you in the right directory?\n")
        sys.exit(1)

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
    """Check if env is ready to proceed"""
    if not os.environ.get('OS_AUTH_URL', False):
        sys.stderr.write("### ERROR ### You need to source the openstack credentials file\n")
        sys.exit(1)

    if os.path.exists('deployment-template'):
        sys.stderr.write("### ERROR ### Did you run 'rega init'? If so, please navigate to your environment folder\n")
        sys.exit(1)

    if not os.path.isfile('terraform.tfvars'):
        sys.stderr.write("### ERROR ### terraform.tfvars not found. Please check you are in your environment folder\n")
        sys.exit(1)


def check_init_dir():
    """Make sure the template folder is present"""
    if not os.path.exists('deployment-template'):
        sys.stderr.write("### ERROR ### deployment-template folder not found. Are you in the right directory?\n")
        sys.exit(1)


def check_version(target_package):
    """Prints out current and original package versions"""
    with open('.version', 'r') as version_file:
        env_package = version_file.readline()

    t = PrettyTable(['Original', 'Current'])
    t.add_row([env_package, target_package])

    if env_package != target_package:
        sys.stderr.write("### WARNING ### The rega environment was created with a different package version\n")
        print(t)
    else:
        logging.info("The rega environment's package version matches with the original version\n")


def create_key_pair():
    """Createds a RSA key pair"""
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
    """Generate Ansible vars file"""
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
    """Retrieves OS and TF specific env vars."""
    for key, val in seq.items():
        if key.startswith('TF_'):
            yield key + '=' + val
        elif key.startswith('OS_'):
            yield key + '=' + val
            yield 'TF_VAR_' + key.lower() + '=' + val
