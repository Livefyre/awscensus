import collections
import threading
import Queue
import os

from datetime import datetime
from datetime import timedelta

import simplejson as json

import boto

import aws.config
import ec2.instances


METRICS_DATA = out = os.path.join(os.getcwd(), "metrics.json")


def dumps(data):
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))


def get():
    mapper = collections.OrderedDict([
        ('CPUUtilizationPercent', 'cpu'),
        ('CPUCreditBalanceCount', 'cpu_cred'),
        ('DiskReadBytes', 'rd_bytes'),
        ('DiskReadOpsCount', 'rd_ops'),
        ('DiskWriteBytes', 'wr_bytes'),
        ('DiskWriteOpsCount', 'wr_ops'),
        ('NetworkInBytes', 'ni'),
        ('NetworkOutBytes', 'no'),
        ('MemoryUsedBytes', 'mem',)])

    perctiles = ('50', '95', '99')

    DEFAULT = {'50': '', '95': '', '99': ''}

    def mb(n):
        return int(float(n)/1024/1024)

    ret = {}
    data = json.loads(open(METRICS_DATA).read())
    for id, metrics in data.iteritems():
        row = {}
        for lng, short in mapper.iteritems():
            f = int if short.startswith('cpu') or short.endswith('_ops') else mb
            for perctile in perctiles:
                row['%s_%s' % (short, perctile)] = (
                    f(metrics.get(lng, DEFAULT)[perctile] or -1))
        ret[id] = row
    return ret


def refresh_instance(instance, config):
    CW_METRIC_NAMES = [
        ['CPUUtilization', 'Percent'],
        ['CPUCreditBalance', 'Count'],
        ['DiskWriteBytes', 'Bytes'],
        ['DiskReadBytes', 'Bytes'],
        ['DiskWriteOps', 'Count'],
        ['DiskReadOps', 'Count'],
        ['NetworkIn', 'Bytes'],
        ['NetworkOut', 'Bytes'], ]

    # timeframe and period (2 weeks, and 20-minute period for AWS. No option to
    # set period for New Relic)
    START = datetime.now() - timedelta(days=14)
    # subtract a minute to get better granularity on New Relic metrics
    END = datetime.now() - timedelta(minutes=1)
    PERIOD = 1200  # 20 minutes

    id = instance['id']
    env = instance['env']

    ret = {'id': id}

    cw = boto.connect_cloudwatch(
        aws_access_key_id=config['aws_ec2']['aws_access_key'],
        aws_secret_access_key=config['aws_ec2']['aws_secret_key'])

    for metric, unit in CW_METRIC_NAMES:
        timeseries = cw.get_metric_statistics(
            period=PERIOD,
            start_time=START,
            end_time=END,
            metric_name=metric,
            namespace='AWS/EC2',
            statistics='Average',
            dimensions={'InstanceId': [id]},
            unit=unit)

        if not timeseries:
            median = ''
            perctile_95 = ''
            perctile_99 = ''
        else:
            sorted_by_value = sorted(timeseries, key=lambda k: k['Average'])
            total_length = len(sorted_by_value)
            median = sorted_by_value[int(total_length/2)]['Average']
            perctile_95 = sorted_by_value[int(0.95*total_length)]['Average']
            perctile_99 = sorted_by_value[int(0.99*total_length)]['Average']

        # append unit to metric name, unless it's already part of the name
        metric_key = (metric+unit if unit not in metric else metric)
        ret[metric_key] = {'50': median, '95': perctile_95, '99': perctile_99}
    return ret


def refresh(conf, workers=1):

    print 'fetching instances...'
    envs = aws.config.get_envs(conf)

    print 'queuing work...'
    upstream = Queue.Queue()
    downstream = Queue.Queue()
    instances = []
    for env in envs:
      env_instances = ec2.instances.get([env], refresh=True)
      for instance in env_instances:
          upstream.put( (instance, env) )
      instances += env_instances

    def worker():
        while True:
            (instance, config) = upstream.get()
            metrics = refresh_instance(instance, config)
            downstream.put(metrics)
            upstream.task_done()

    # start threads
    for _ in range(workers):
        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()

    data = {}
    for _ in instances:
        metrics = downstream.get()
        id = metrics.pop('id')
        data[id] = metrics
        print id
        downstream.task_done()

    open(METRICS_DATA, 'w').write(dumps(data))
