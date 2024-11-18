#!/usr/bin/env python
from setuptools import setup, find_packages
from setuptools.command.install import install as InstallCommand


class Install(InstallCommand):
    def run(self, *args, **kwargs):
        import pip
        pip.main(["-H", "None", "-f", "./deps", "Requests>=2.6.0"])
        InstallCommand.run(self, *args, **kwargs)

setup(
    name="nagini",
    version="2.0",
    description="This module contains code for making REST calls to VMware Aria Operations.",
    author="VMware Aria Operations API team",
    url="http://www.vmware.com",
    include_package_data=True,
    package_data={"nagini": ["methods.json"]},
    packages=["nagini"],
)
