from setuptools import setup, find_packages

setup(
    name='rega',
    version='0.5.0',
    packages=find_packages(),
    py_modules=['rega'],
    include_package_data=True,
    description='REGA CLI for provisioning RKE clusters',
    author='Jon Ander Novella',
    install_requires=[
        'click==7.0',
        'pyhcl==0.3.12',
        'jinja2==2.10.1',
        'click-plugins==1.1.1',
        'docker==4.0.1',
        'cryptography==2.7',
        'flake8==3.7.7',
        'PyYAML==5.1.1'
    ],
    entry_points='''
        [console_scripts]
        rega=rega:main
    '''
)
