import sys
import os
import subprocess
import click
import docker
import logging
from distutils import dir_util
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from os import walk
from pkg_resources import iter_entry_points
from click_plugins import with_plugins
from distutils import dir_util

logging.basicConfig(level=logging.INFO)

volume_mount = {os.getcwd(): {'bind': '/mnt/deployment/', 'mode': 'rw'}}
container_wd = '/mnt/deployment/'
default_image = 'novella/rega:latest'

@click.group()
def main():
    """REGA is a tool for provisioning RKE clusters."""
@main.command('init')
@click.argument('dir')
@click.option('-I','--image', default=default_image, envvar='REGA_PROVISIONER_IMG')
def init(dir,image):
    logging.info("""Command init executed and passed argument {}""".format(dir))
    client = docker.from_env()
    client.images.pull(image)
    check_init_dir()
    create_deployment(dir)

@main.command('version')
@click.option('-I','--image', default=default_image, envvar='REGA_PROVISIONER_IMG')
def version(image):
    logging.info("""REGA provisioner version is {}""".format(image))

@main.command('openstack')
@click.argument('extra_args')
@click.option('-I','--image', default=default_image, envvar='REGA_PROVISIONER_IMG')
def openstack(extra_args,image):
    #client.images.pull(image)
    logging.info("""Command openstack executed and passed argument {}""".format(extra_args))
    client = docker.from_env()
    output = client.containers.run(image, 'openstack {}'.format(extra_args))
    logging.info('OPENSTACK: {}'.format(output))

@main.command('apply')
@click.option('-I','--image', default=default_image, envvar='REGA_PROVISIONER_IMG')
def apply(image):
    #client.images.pull(image)
    logging.info("""Command apply executed""")
    env = list(filter_vars(os.environ))
    check_environment()
    client = docker.from_env()
    command_init = 'terraform init -plugin-dir=/terraform_plugins && '
    command_apply = 'terraform apply -auto-approve'
    commands = '"' + command_init + command_apply + '"'
    container_apply = client.containers.run(image, volumes=volume_mount,\
    environment=env,working_dir=container_wd,\
    entrypoint= ['bash', '-c'],command=commands,detach=True)
    log_stream = container_apply.logs(stream=True,follow=True)
    for line in log_stream:
        print(line.decode())

@main.command('destroy')
@click.option('-I','--image', default=default_image, envvar='REGA_PROVISIONER_IMG')
def destroy(image):
    #client.images.pull(image)
    logging.info("""Command destroy executed""")
    env = list(filter_vars(os.environ))
    check_environment()
    client = docker.from_env()
    command_destroy = 'terraform destroy -force'
    container_destroy = client.containers.run(image, volumes=volume_mount,\
    environment=env, working_dir=container_wd,\
    command=command_destroy, detach=True)
    log_stream = container_destroy.logs(stream=True,follow=True)
    for line in log_stream:
        print(line.decode())

@main.command('state')
@click.argument('extra_args')
@click.option('-I','--image', default=default_image, envvar='REGA_PROVISIONER_IMG')
def state(extra_args,image):
    #client.images.pull(image)
    logging.info("""State command executed""")
    env = list(filter_vars(os.environ))
    check_environment()
    client = docker.from_env()
    command_state = 'terraform state {}'.format(extra_args)
    output_state = client.containers.run(image ,volumes=volume_mount,\
    environment=env, working_dir=container_wd, command=command_state)
    logging.info('STATE: {}'.format(output_state))

def create_deployment(dir):
    """copy relevant files to new folder"""
    if os.path.exists('deployment-template'):
        dir_util.mkpath(dir)
        subprocess.call('cp -r deployment-template/* ./{}/'.format(dir), shell=True)
    else:
        sys.stderr.write("Error: deploymenttemplate folder not found. Are you in the right directory?\n")
        sys.exit(1)

    if not os.path.isfile(dir + '/ssh_key.pub'):
        pu, pv = create_key_pair()
        with open(dir + '/ssh_key.pub', 'w') as key:
            key.write(pu)
        with open(dir + '/ssh_key', 'w') as key:
            key.write(pv)

def check_environment():
    if not os.environ.get('OS_AUTH_URL', False):
        sys.stderr.write("Error: You need to source the openstack credentials file\n")
        sys.exit(1)

    if not os.path.isfile('ssh_key.pub'):
        sys.stderr.write("Error: ssh_key not found. Are you in the right directory?\n")
        sys.exit(1)

    if not os.path.isfile('terraform.tfvars'):
        sys.stderr.write("Error: terraform.tfvars not found. Are you in the right directory?\n")
        sys.exit(1)

def check_init_dir():
    if not os.path.exists('deployment-template'):
        sys.stderr.write("Error: deployment-template folder not found. Are you in the right directory?\n")
        sys.exit(1)

def create_key_pair():
    key = rsa.generate_private_key(
        backend=crypto_default_backend(),
        public_exponent=65537,
        key_size=2048
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
   for key, val in seq.items():
       if key.startswith('TF_'): yield key+'='+val
       elif key.startswith('OS_'): yield key+'='+val
