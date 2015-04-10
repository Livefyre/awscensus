import urllib
import os
import glob

import simplejson as json
import demjson


#TODO THIS IS NOT WHERE WE WANT TO PLACE THIS...
DATAPATH = os.getcwd()


def mkdirp(path):
    try:
        os.makedirs(path)
    except:
        pass


def refresh():
    sources = [(
        'old',
        'http://a0.awsstatic.com/pricing/1/ec2/previous-generation/',
    ), (
        'new',
        'http://a0.awsstatic.com/pricing/1/ec2/',
    )]

    files = ('linux-od.min.js', 'ri-v2/linux-unix-shared.min.js')

    print 'this takes a while; like 10 mins. demjson is slllloooooww.'
    print

    for age, uri in sources:
        for file in files:
            print uri+file
            s = urllib.urlopen(uri+file).read()
            s = s[s.find('{'):-2]
            data = demjson.decode(s)
            out = '%s/%s.%s.json' % (DATAPATH, age, os.path.basename(file))
            open(out, 'w').write(json.dumps(data)) #TODO USE SAFEOUTPUT HERE.


def get(inputs):
    specs = {}

    def parse_od(data):
        instance_types = [
            x for x in data['config']['regions']
            if x['region'] == 'us-east-1'][0]['instanceTypes']

        for instance_type in instance_types:
            for size in instance_type['sizes']:
                instance = specs.setdefault(size['size'], {})
                prices = instance.setdefault('prices', {})
                instance['mem'] = size['memoryGiB']
                instance['vcpu'] = size['vCPU']
                instance['ecu'] = \
                    size['ECU'] != 'variable' and size['ECU'] or 0
                storage = size['storageGB']
                if storage != 'ebsonly':
                    storage = storage.split(' x ')
                    num_drives = len(storage) == 1 and 1 or int(storage[0])
                    capacity = storage[-1]
                    if capacity.endswith('SSD'):
                        ssd = True
                        capacity = capacity[:-4]
                    elif capacity.endswith('HDD'):
                        ssd = False
                        capacity = capacity[:-4]
                    else:
                        ssd = False
                    capacity = int(capacity)
                    instance['storage'] = (
                        num_drives, capacity, num_drives*capacity, ssd)
                else:
                    instance['storage'] = (0, 0, 0, False)
                prices['od'] = float(
                    size['valueColumns'][0]['prices']['USD'])

    def parse_shared(data):
        instance_types = [
            x for x in data['config']['regions']
            if x['region'] == 'us-east-1'][0]['instanceTypes']

        for instance_type in instance_types:
            instance = specs.setdefault(instance_type['type'], {})
            prices = instance.setdefault('prices', {})
            for term in instance_type['terms']:
                t = term['term'][-1]
                for option in term['purchaseOptions']:
                    o = option['purchaseOption'][0]
                    prices[t+o+'d'] = option['savingsOverOD']
                    option_prices = dict(
                        (x['name'][0], x['prices']['USD'])
                        for x in option['valueColumns'])
                    if o in 'ap':
                        try:
                            prices[t+o+'u'] = float(option_prices['u'])
                        except ValueError:
                            pass
                    if o in 'np':
                        try:
                            prices[t+o+'m'] = float(option_prices['m'])
                        except ValueError:
                            pass

    for name in inputs:
        data = json.loads(open(name).read())
        if 'od' in name:
            parse_od(data)
        else:
            parse_shared(data)

    return specs
