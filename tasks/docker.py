#!/usr/bin/env python
# -*- coding: UTF-8 -*-

#  Copyright (C) 2024. Suto-Commune
#  _
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#  _
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#  _
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
@File       : docker.py

@Author     : hsn

@Date       : 2024/11/12 上午11:52
"""

import subprocess

from invoke import task, Collection


@task
def build(c):
    import tomllib
    with open('config.toml', 'rb') as f:
        toml = tomllib.load(f)
    version = toml['project']['version']
    name = toml['project']['name']
    subprocess.run(
        f'docker build -t hsn8086/{name}:{version} .&&docker tag hsn8086/{name}:{version} hsn8086/{name}:latest',
        shell=True)


@task
def push(c):
    import tomllib
    with open('config.toml', 'rb') as f:
        toml = tomllib.load(f)
    version = toml['project']['version']
    name = toml['project']['name']
    subprocess.run(f'docker push hsn8086/{name}:{version}&&docker push hsn8086/{name}:latest', shell=True)


@task(pre=[build])
def compose(c):
    subprocess.run('docker-compose up --build', shell=True)


namespace = Collection(build, push, compose)
