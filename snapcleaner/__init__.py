#!/usr/bin/env python

from    argparse import ArgumentParser
import  boto
from    datetime import datetime, timedelta
from    pyyacc.parser import build
import  os

import ec2.config

time_format="%Y-%m-%dT%H:%M:%S.000Z"

def get_time_horizon(args):
    days = args.days
    seconds = args.seconds
    minutes = args.minutes
    hours = args.hours
    weeks = args.weeks
    if days == seconds == minutes == hours == weeks == 0:
        raise ValueError("Must specify a time period")
    return timedelta(days, seconds, 0, 0, minutes, hours, weeks)

def get_snaps_to_delete(conn, time_horizon):
    now = datetime.utcnow()
    snaps = conn.get_all_snapshots(owner='self')
    delete_snaps = filter( lambda snap: now - datetime.strptime(snap.start_time, time_format) > time_horizon, snaps) 
    return delete_snaps

def print_snaps(snaps):
    for snap in snaps:
        print snap.id, snap.volume_id, snap.start_time, snap.status, snap.description.strip()
 
def prompt_yes_no(prompt = 'Please enter Yes/No: '):
    while True:
        try:
            i = raw_input(prompt)
        except KeyboardInterrupt:
            return False
        if i.lower() in ('yes','y'): 
            return True
        elif i.lower() in ('no','n'): 
            return False

def delete_snaps(snaps):
    for snap in snaps:
        try:
            print "Deleting snap", snap.id, snap.volume_id, snap.description.strip(), "..."
            snap.delete()
        except boto.exception.EC2ResponseError as e:
            print dir(e)
            print "Delete failed because %s" % e.body
        else:
            print "done"

parser = ArgumentParser(description='Manages ebs volumes.')
parser.add_argument('--noop', action='store_true')
parser.add_argument('--force', action='store_true')
parser.add_argument('--days', type=int, default=0)
parser.add_argument('--seconds', type=int, default=0)
parser.add_argument('--minutes', type=int, default=0)
parser.add_argument('--hours', type=int, default=0)
parser.add_argument('--weeks', type=int, default=0)
parser.add_argument('--config', type=str)

def main():
    args = parser.parse_args()
    if args.config is not None:
        conf = args.config.split(",")
    else:
        conf = list()

    envs = ec2.config.get_envs(conf)

    for env in envs:
        access_key = env['aws_ec2']['aws_access_key']
        secret_key = env['aws_ec2']['aws_secret_key']
        time_horizon = get_time_horizon(args)
        conn = boto.connect_ec2(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        del_snaps = get_snaps_to_delete(conn, time_horizon)
        print_snaps(del_snaps)
        if args.noop:
            exit(0)
        if not args.force:
            print "Should I delete these snaps"
            if not prompt_yes_no():
                print "Exiting without deleting snaps."
                exit(0)
            delete_snaps(del_snaps)

