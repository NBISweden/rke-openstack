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

logging.basicConfig(level=logging.INFO)
DEFAULT_IMAGE = f'nbisweden/rega:release-v{pkg_resources.get_distribution("rega").version}'


@click.group()
def main():
    """REGA is a tool for provisioning RKE clusters."""


@main.command('init')
@click.argument('dir')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG')
def init(dir, image):
    """Initialises a new REGA environment."""
    logging.info("""Initilising a new environment in {}""".format(dir))
    client = docker.from_env()
    client.images.pull(image)
    check_init_dir()
    create_deployment(dir)
    logging.info("""Environment initialised. Navigate to the {} folder and update the terraform.tfvars file with your configuration""".format(dir))


@main.command('version')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG')
def version(image):
    """Outputs the version of the provisioning container and the CLI."""
    print("""REGA provisioner version: {}""".format(image))
    print("""REGA CLI version: {}""".format(pkg_resources.get_distribution("rega").version))


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
    check_environment()
    tf_modules = get_tf_modules(modules)
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
    run_in_container(['terraform {}'.format(extra_args)], image)


@main.command('openstack')
@click.argument('extra_args')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def openstack(extra_args, image):
    """Executes the openstack command in the provisioner container with the provided args."""
    logging.info("""Running openstack with arguments: {}""".format(extra_args))
    run_in_container(['openstack {}'.format(extra_args)], image)


@main.command('provision')
@click.argument('extra_args')
@click.option('-I', '--image', default=DEFAULT_IMAGE,
              envvar='REGA_PROVISIONER_IMG',
              help='Docker image used for provisioning')
def provision(image, extra_args):
    """Executes the Ansible playbook specified as an argument."""
    check_environment()
    generate_vars_file()
    run_ansible(extra_args, image)


def run_in_container(commands, image):
    client = docker.from_env()
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


def terraform_apply(modules, image, backend, config):
    main_out = render('main.j2', {'backend_type': backend})
    main_out = main_out.decode('utf-8')
    main_file = open('main.tf', 'w')
    main_file.write(main_out)
    main_file.close()
    return run_in_container(['terraform init -backend-config={} -plugin-dir=/terraform_plugins'.format(config),
                             'terraform apply -auto-approve {}'.format(modules)], image)


def run_ansible(playbook, image):
    return run_in_container(['ansible-playbook playbooks/{}'.format(playbook)], image)


def create_deployment(dir):
    """Copy relevant files to new folder."""
    if os.path.exists('deployment-template'):
        dir_util.mkpath(dir)
        dir_util.copy_tree('deployment-template/', './{}/'.format(dir))
    else:
        sys.stderr.write("Error: deployment-template folder not found. Are you in the right directory?\n")
        sys.exit(1)

    if not os.path.isfile(dir + '/ssh_key.pub'):
        pu, pv = create_key_pair()
        with open(dir + '/ssh_key.pub', 'w') as key:
            key.write(pu)
        with open(dir + '/ssh_key', 'w') as key:
            key.write(pv)
            os.chmod(dir + '/ssh_key', 0o400)


def check_environment():
    if not os.environ.get('OS_AUTH_URL', False):
        sys.stderr.write("Error: You need to source the openstack credentials file\n")
        sys.exit(1)

    if os.path.exists('deployment-template'):
        sys.stderr.write("Error: Did you run 'rega init'? If so, please navigate to your environment folder\n")
        sys.exit(1)

    if not os.path.isfile('terraform.tfvars'):
        sys.stderr.write("Error: terraform.tfvars not found. Please check you are in your environment folder\n")
        sys.exit(1)


def check_init_dir():
    if not os.path.exists('deployment-template'):
        sys.stderr.write("Error: deployment-template folder not found. Are you in the right directory?\n")
        sys.exit(1)


def create_key_pair():
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
    for key, val in seq.items():
        if key.startswith('TF_'):
            yield key + '=' + val
        elif key.startswith('OS_'):
            yield key + '=' + val
            yield 'TF_VAR_' + key.lower() + '=' + val
