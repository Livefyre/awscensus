import re

import boto.ec2

import ec2.metrics
import ec2.specs


def ec2_conn(env):
    return boto.ec2.connect_to_region(
        env['aws_ec2']['aws_region'],
        aws_access_key_id=env['aws_ec2']['aws_access_key'],
        aws_secret_access_key=env['aws_ec2']['aws_secret_key'])


def pull(env):
    """
    pulls interesting fields for all instances in the supplied envs from aws
    """
    interesting = [
        'id',
        'instance_type',
        'launch_time',
        'placement',
        'state',
        'tags',
        'virtualization_type',
        'vpc_id', ]

    instances = []
    conn = ec2_conn(env)
    for reservation in conn.get_all_instances():
        for instance in reservation.instances:
            data = {}
            for x in interesting:
                data[x] = getattr(instance, x)
            instances.append(data)
    return instances


def cook(instances):
    """
    takes a list of instances as retured by *pull* and normalizes the data to a
    useful form
    """
    vpcs = {}

    for instance in instances:
        vpc_id = instance['vpc_id']
        tags = instance['tags']
        if vpc_id and vpc_id not in vpcs:
            if 'Name' in tags:
                parts = tags['Name'].split('.')
                if len(parts) == 4:
                    vpcs[vpc_id] = parts[1]

    def env(instance):
        vpc_id = instance['vpc_id']
        tags = instance['tags']
        if vpc_id in vpcs:
            return vpcs[vpc_id]
        if 'Name' in tags:
            parts = tags['Name'].split('.')
            if len(parts) == 4:
                return parts[1]
        return 'unknown'

    def role(instance):
        tags = instance['tags']
        if 'role' in tags:
            return tags['role']
        if 'Name' in tags:
            prefix = tags['Name'].split('.')[0]
            match = re.match('^([a-z]*)\d', prefix)
            if match:
                return match.group(1)
        return 'unknown'

    columns = [
        ('role', lambda i: role(i)),
        ('env', lambda i: env(i)),
        ('host', lambda i: i['tags'].get('Name')),
        ('az', lambda i: i['placement']),
        ('type', lambda i: i['instance_type']),
        ('time', lambda i: i['launch_time']),
        ('virt', lambda i: i['virtualization_type']),
        ('state', None),
        ('id', None), ]

    cooked = []
    for instance in instances:
        row = {}
        for key, f in columns:
            f = f or (lambda i: instance[key])
            row[key] = f(instance)
        cooked.append(row)
    return cooked

#TODO THIS FUNCTION IS KINDA A BAD IDEA... IT SHOULD BE A PROGRAM ITSELF?
def get(envs, refresh=False):
    instances = []
    for env in envs:
        instances += pull(env)
    return cook(instances)


# lazy load and cache shared instance data
class DATA(object):
    def __init__(self):
        self._metrics = None
        self._specs = None

    @property
    def metrics(self):
        if not self._metrics:
            self._metrics = ec2.metrics.get()
        return self._metrics

    @property
    def specs(self):
        if not self._specs:
            self._specs = ec2.specs.get()
        return self._specs

DATA = DATA()


class Group(object):
    """
    represents a group of instances
    """
    def __init__(self, key):
        self.key = key
        self.instances = []

    def __getattr__(self, name):
        if name in self.instances[0]:
            return self.instances[0][name]
        raise AttributeError(name)

    def price(self, name, instance_type=None):
        prices = [
            DATA.specs[
                instance_type and instance_type or x['type']]['prices'][name]
            for x in self.instances]
        return sum(prices)

    def metric(self, name):
        members = [x[name] for x in self.metrics]
        if not members:
            return -1
        return sum(members) / len(members)

    @property
    def metrics(self):
        return [
            DATA.metrics[x['id']]
            for x in self.instances if x['id'] in DATA.metrics]

    @property
    def type(self):
        return list(set([x['type'] for x in self.instances]))

    @property
    def new(self):
        return bool([
            x for x in self.instances if x['virt'] == 'hvm'])

    def __len__(self):
        return len(self.instances)

    def __repr__(self):
        return 'Group(%s: %s)' % (self.key, len(self.instances))
