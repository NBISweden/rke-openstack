from setuptools import setup

setup(
    name='rega',
    version='1.5.0',
    packages=['rega'],
    description='REGA CLI for provisioning RKE clusters',
    author='Jon Ander Novella',
    install_requires=[
        'click==7.0',
        'pyhcl==0.3.12',
        'click-plugins==1.1.1',
        'docker==4.0.1',
        'cryptography==2.7',
        'PyYAML==5.1.1',
        'prettytable==0.7.2'
    ],
    setup_requires=[
        'flake8==3.7.7',
        'tox>=3.14.0',
    ],
    entry_points='''
        [console_scripts]
        rega=rega.cmd:main
    '''
)
