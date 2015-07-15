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
import requests
import json

import ec2.instances
import ec2.config

def pdb_query(base_path, q_string = {'query':''}):
    headers = {"Accept": "application/json"}
    host = "http://puppetdb:8080"
    r = requests.get(host+base_path, params=q_string, headers=headers)
    retval = r.json()
    return retval

def get_host_list():
    node_list = [(node['certname'].strip(),node['value'].strip()) for node in pdb_query("/v2/facts/ec2_instance_id")]
    return node_list

def main():
    args = docopt(usage)
    if args['--config'] is not None:
        conf = args['--config'].split(",")
    else:
        conf = list()

    envs = ec2.config.get_envs(conf)
    instances = ec2.instances.get(envs, refresh=True)
    not_termed = [x for x in instances if x['state'] not in ("terminated")]
    exists = set([x['id'] for x in not_termed])

    hosts = get_host_list()

    for hostname, instanceid in hosts:
        if instanceid not in exists:
            print hostname
            if args['--nodry']:
                subprocess.call(
                    'sudo puppet node deactivate %s' % hostname, shell=True)
                subprocess.call(
                    'sudo puppet cert clean %s' % hostname, shell=True)

