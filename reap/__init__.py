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
    node_list = [node['certname'] for node in pdb_query("/v2/resources/Class/Lf_base")]
    return node_list

def main():
    args = docopt(usage)

    hosts = get_host_list()
    hosts = [x.strip() for x in hosts]

    for host in hosts:
        print host
