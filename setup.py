from setuptools import setup

setup(
    name='rega',
    version='2.0.0',
    packages=['rega'],
    description='REGA CLI for provisioning RKE clusters',
    author='Jon Ander Novella and Johan Viklund',
    entry_points='''
        [console_scripts]
        rega=rega.cmd:main
    '''
)
