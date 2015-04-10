#!/usr/bin/env python

usage = \
"""
Usage:
    reap [options]

Options:
    --nodry
    --config <conf>    Config file
"""

import subprocess
import sys
import os

from docopt import docopt

import ec2.instances
import ec2.config


def main():
    args = docopt(usage)
    if args['--config'] is not None:
        conf = args['--config'].split(",")
    else:
        conf = list()

    envs = ec2.config.get_envs(conf)
    instances = ec2.instances.get(envs, refresh=True)
    exists = set([x['host'] for x in instances])

    hosts = subprocess.check_output('marionette show_hosts', shell=True)
    hosts = [x.strip() for x in hosts.strip().split()]

    for host in hosts:
        if host not in exists:
            print host
            if args['--nodry']:
                subprocess.call(
                    'sudo puppet node deactivate %s' % host, shell=True)
                subprocess.call(
                    'sudo puppet cert clean %s' % host, shell=True)

