from setuptools import setup, find_packages

setup(
    name='rega',
    version='0.3.4',
    packages=find_packages(),
    py_modules=['rega'],
    include_package_data=True,
    description='REGA CLI for provisioning RKE clusters',
    author='Jon Ander Novella',
    install_requires=[
        'click==7.0',
        'pyhcl==0.3.11',
        'click-plugins==1.0.4',
        'docker==3.7.0',
        'cryptography==2.5.0',
        'flake8==3.7.7',
        'PyYAML==5.1'
    ],
    entry_points='''
        [console_scripts]
        rega=rega:main
    '''
)
