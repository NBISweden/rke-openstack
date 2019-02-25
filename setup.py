from setuptools import setup, find_packages

setup(
    name='rega',
    version='0.2.4',
    packages=find_packages(),
    py_modules=['rega'],
    include_package_data=True,
    description='REGA CLI for provisioning RKE clusters',
    author='Jon Ander Novella',
    install_requires=[
        'click>=6.7',
        'click-plugins',
        'docker==2.0.0',
        'cryptography==2.5.0'
    ],
    entry_points='''
        [console_scripts]
        rega=rega:main
    '''
)
