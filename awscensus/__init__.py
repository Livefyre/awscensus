#!/usr/bin/env python

usage = \
"""
Usage:
    awscensus specs refresh
    awscensus specs list <inputs>... [--csv]
    awscensus metrics refresh [--config=<conf> --workers=<workers>]
    awscensus metrics list [--csv]
    awscensus instances list [--config=<conf> --csv]
    awscensus instances grouped [--config=<conf> --csv]
    awscensus purchased [--config=<conf> --csv]

Options:
    --workers=INT  Number of threads [default: 1]
    --config <conf>    Config file
"""


import sys
import os

import simplejson as json

from docopt import docopt

import aws.config
import ec2.instances
import ec2.tabular
import ec2.metrics
import ec2.specs
import ec2.purchased


def mkdirp(path):
    try:
        os.makedirs(path)
    except:
        pass


def dumps(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def do_specs_list(inputs, csv=False):
    specs = ec2.specs.get(inputs)

    main = ['vcpu', 'ecu', 'mem']
    storage = ['num', 'cap', 'tot', 'ssd']
    prices = ['odu', 'odm', '1au', '1am', '1nu', '1nm', '1pu', '1pm']

    def getter(col):
        def get(row):
            name, instance = row
            if col == 'name':
                return name
            if col in main:
                return instance[col]
            if col in storage:
                value = instance['storage'][storage.index(col)]
                if col == 'ssd':
                    value = value and 'y' or 'n'
                return value

            # on demand monthly
            if col == 'odm':
                value = instance['prices'].get('od', 0) * 24 * 30
            else:
                value = instance['prices'].get(col, 0) or 0
            return value
        return get

    if csv:
        to_human = {
            'num': 'storage - num',
            'cap': 'storage - cap',
            'tot': 'storage - tot',
            'ssd': 'storage - ssd',
            'odu': 'on demand - upfront',
            'odm': 'on demand - monthly',
            '1au': '1 year term all upfront - upfront',
            '1am': '1 year term all upfront - monthly',
            '1nu': '1 year term no upfront - upfront',
            '1nm': '1 year term no upfront - monthly',
            '1pu': '1 year term partial upfront - upfront',
            '1pm': '1 year term partial upfront - monthly', }

    else:
        # headers are too long for console output
        to_human = {}

    columns = [('name', lambda m: m[0])] + [
        (to_human.get(name, name), getter(name))
        for name in main + storage + prices]

    if csv:
        ec2.tabular.pcsv(columns, specs.items())
    else:
        ec2.tabular.pprint(columns, specs.items())


def do_metrics_list(csv=False):
    metrics = ec2.metrics.get()

    categories = [
        'cpu', 'rd_bytes', 'rd_ops', 'wr_bytes', 'wr_ops', 'ni', 'no']
    perctiles = ('50', '90', '99')
    names = ['%s_%s' % (c, p) for c in categories for p in perctiles]

    def getter(name):
        def get(m):
            return m[1][name]
        return get
    columns = [('id', lambda m: m[0])] + [
        (name, getter(name)) for name in names]

    if csv:
        ec2.tabular.pcsv(columns, metrics.items())
    else:
        ec2.tabular.pprint(columns, metrics.items())


def do_instances_list(envs, csv=False):
    instances = ec2.instances.get(envs) #TODO DIRTY

    def getter(col):
        def get(row):
            return row[col]
        return get

    columns = [(name, getter(name)) for name in [
        'id', 'role', 'env', 'host', 'az', 'type', 'time', 'virt', 'state']]

    if csv:
        ec2.tabular.pcsv(columns, instances)
    else:
        ec2.tabular.pprint(columns, instances)


def do_instances_grouped(envs, csv=False):
    instances = ec2.instances.get(envs) #TODO DIRTY
    groups = {}

    for instance in instances:
        if instance['state'] != 'running':
            continue
        key = '%s-%s-%s' % (
            instance['env'], instance['role'], instance['type'])
        g = groups.setdefault(key, ec2.instances.Group(key))
        g.instances.append(instance)

    columns = [
        ('env', lambda g: g.env),
        ('role', lambda g: g.role),
        ('num', lambda g: len(g)),
        ('cpu_90', lambda g: g.metric('cpu_90')),
        ('virt', lambda g: g.virt),
        ('type', lambda g: g.type[0]), ]

    if csv:
        ec2.tabular.pcsv(columns, groups.values())
    else:
        ec2.tabular.pprint(columns, groups.values())

def do_purchased_list(accts, csv=False):
    ris = ec2.purchased.get(accts)

    def getter(col):
        def get(row):
            return row[col]
        return get

    columns = [(name, getter(name)) for name in [
        'account', 'az', 'type', 'count']]

    if csv:
        ec2.tabular.pcsv(columns, ris)
    else:
        ec2.tabular.pprint(columns, ris)

def main():
    args = docopt(usage)
    if args['--config'] is not None:
        conf = args['--config'].split(",")
    else:
        conf = list()

    if args['specs']:
        if args['refresh']:
            return ec2.specs.refresh()

        if args['list']:
            return do_specs_list(args['<inputs>'], csv=args['--csv'])

    if args['metrics']:
        if args['refresh']:
            return ec2.metrics.refresh(
                conf, workers=int(args["--workers"]))

        if args['list']:
            return do_metrics_list(csv=args['--csv'])

    if args['instances']:
        envs = aws.config.get_envs(conf)

        if args['list']:
            return do_instances_list(envs, csv=args['--csv']) #TODO DIRTY

        if args['grouped']:
            return do_instances_grouped(envs, csv=args['--csv']) #TODO DIRTY

    if args['purchased']:
        accts = aws.config.get_envs(conf)

        return do_purchased_list(accts, csv=args['--csv'])

