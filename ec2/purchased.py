import sys
import boto.ec2

import ec2.instances

def get(accts):
    ris = {}
    for acct in accts:
        conn = ec2.instances.ec2_conn(acct)
        acct_name = acct['name']
        for ri in conn.get_all_reserved_instances():
            if ri.state != 'active':
                sys.stderr.write("RI %s excluded because it's not active\n" % ri.id)
            else:
                az = ri.availability_zone
                instance_type = ri.instance_type
                ris[(acct_name, az, instance_type)] = ris.get((acct_name, az, instance_type), 0) + ri.instance_count

    ri_list = [{'account':a, "az":z, "type":t, "count":c} for ((a,z,t),c) in ris.items()]
    return ri_list

