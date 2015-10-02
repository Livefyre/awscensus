#!/usr/bin/env python

usage = \
"""
Usage:
    billing cloudfront [--config=<conf> --bucket=<bucket> --acct-id=<acct_id>]

Options:
    --config <conf>     Config file
    --bucket <bucket>   Billing bucket name
    --acct-id <acct_id> AMZ Payer Account ID
"""

import zipfile
import sys
from decimal import *
import datetime
import re
import boto
from docopt import docopt

import aws.config

from csvorm import (
    Model,
    Column,
    Integer,
    Unicode,
    DateTime,
    )

class BillCSV(Model):
    _encoding_ = 'utf-8'
    InvoiceID=Column(Unicode)
    PayerAccountId=Column(Unicode)
    LinkedAccountId=Column(Unicode)
    RecordType=Column(Unicode)
    ProductName=Column(Unicode)
    RateId=Column(Unicode)
    SubscriptionId=Column(Unicode)
    PricingPlanId=Column(Unicode)
    UsageType=Column(Unicode)
    Operation=Column(Unicode)
    AvailabilityZone=Column(Unicode)
    ReservedInstance=Column(Unicode)
    ItemDescription=Column(Unicode)
    UsageStartDate=Column(Unicode)
    UsageEndDate=Column(Unicode)
    UsageQuantity=Column(Unicode)
    BlendedRate=Column(Unicode)
    BlendedCost=Column(Unicode)
    UnBlendedRate=Column(Unicode)
    UnBlendedCost=Column(Unicode)

class BillPredictionCSV(Model):
    _encoding_ = 'utf-8'
    Region=Column(Unicode)
    HTTP_10kReq=Column(Unicode)
    HTTPS_10kReq=Column(Unicode)
    CostGB=Column(Unicode)
    StartDate=Column(Unicode)
    EndDate=Column(Unicode)
    AccountId=Column(Unicode)
    HttpReq=Column(Unicode)
    HttpsReq=Column(Unicode)
    GB=Column(Unicode)


REGIONS = [
    'AU',
    'EU',
    'AP',
    'IN',
    'JP',
    'SA',
    'US',
]

def s3_conn(acct):
    return boto.connect_s3(
        acct['aws_ec2']['aws_access_key'],
        acct['aws_ec2']['aws_secret_key'])

def get_key_name(acct_id):
    d = datetime.date.today()
    cur_month = d.strftime('%m')
    cur_year  = d.strftime('%Y')
    key_name = '%s-aws-billing-detailed-line-items-%s-%s.csv.zip' % (acct_id, cur_year, cur_month)
    return key_name

def get_bill(acct, bucket, key_name):
    conn = s3_conn(acct)

    b = conn.get_bucket(bucket)
    k = b.get_key(key_name)
    print "Downloading file: %s ..." % key_name
    k.get_contents_to_filename(key_name)

    zf = zipfile.ZipFile(key_name)
    return zf.extract(key_name.replace('.zip',''))

def cloudfront_monthly_prediction(bill_file,csv=False):
    bill_csv = BillCSV()
    bill_csv.load(bill_file)

    memo_dict = {reg: {} for reg in REGIONS}
    acct_ids = set()

    for aws_rec in bill_csv:
        if aws_rec.ProductName == 'Amazon CloudFront':
            usage_type = aws_rec.UsageType
            region = re.search(r"^(\w{2})", usage_type).group(1)
            if 'Requests-HTTP-Proxy' in usage_type:
                memo_dict[region]['HTTP_10kReq'] = re.search(r"\$([0-9.]+) per.*$",aws_rec.ItemDescription).group(1)
            elif 'Requests-HTTPS-Proxy' in usage_type:
                memo_dict[region]['HTTPS_10kReq'] = re.search(r"\$([0-9.]+) per.*$",aws_rec.ItemDescription).group(1)
            elif aws_rec.Operation == 'GET':
                linked_acct = aws_rec.LinkedAccountId
                acct_ids.add(linked_acct)
                usage = aws_rec.UsageQuantity

                #TODO: this is dumb and relies on the 1-hour windows being listed in chronological order, which might not alway be true
                memo_dict[region].setdefault('StartDate', aws_rec.UsageStartDate)
                memo_dict[region]['EndDate'] = aws_rec.UsageEndDate

                memo_dict[region].setdefault('Usage',{})
                memo_dict[region]['Usage'].setdefault(linked_acct, {})

                if 'Requests-Tier1' in usage_type:
                    memo_dict[region]['Usage'][linked_acct]['HttpReq'] = memo_dict[region]['Usage'][linked_acct].get('HttpReq', 0) + Decimal(usage)

                if 'Requests-Tier2-HTTPS' in usage_type:
                    memo_dict[region]['Usage'][linked_acct]['HttpsReq'] = memo_dict[region]['Usage'][linked_acct].get('HttpsReq', 0) + Decimal(usage)

                if 'DataTransfer-Out-Bytes' in usage_type:
                    memo_dict[region]['CostGB'] = re.search(r"\$([0-9.]+) per.*$",aws_rec.ItemDescription).group(1)
                    memo_dict[region]['Usage'][linked_acct]['GB'] = memo_dict[region]['Usage'][linked_acct].get('GB', 0) + Decimal(usage)

    prediction_csv = BillPredictionCSV()
    for region, region_data in memo_dict.iteritems():
        rec = prediction_csv.create()
        rec.Region = region
        rec.CostGB = region_data['CostGB']
        rec.StartDate = region_data['StartDate']
        rec.EndDate = region_data['EndDate']
        rec.HTTP_10kReq = region_data['HTTP_10kReq']
        rec.HTTPS_10kReq = region_data['HTTPS_10kReq']
        for acct_id, usage_data in region_data['Usage'].iteritems():
            rec = prediction_csv.create()
            rec.AccountId = acct_id
            try:
                rec.HttpReq = usage_data['HttpReq']
                rec.HttpsReq = usage_data['HttpsReq']
                rec.GB = usage_data['GB']
            except KeyError, e:
                sys.stderr.write('No data: %s\n' % str(e))
                sys.stderr.write(region + '\n')
                sys.stderr.write(str(acct_id) + '\n')
                sys.stderr.write(str(usage_data) + '\n')

    prediction_csv.dump('cf_bill_prediction.csv')
    return 0


def main():
    args = docopt(usage)
    if args['--config'] is not None:
        conf = args['--config'].split(",")
    else:
        conf = list()

    if args['--acct-id'] is not None:
         acct_id = args['--acct-id']
    else:
        print '--acct-id required'
        return 1

    if args['--bucket'] is not None:
        bucket_name = args['--bucket']
    else:
        print '--bucket required'
        return 1

    creds = aws.config.get_envs(conf)[0]

    key_name = get_key_name(acct_id)
    d = datetime.date.today()
    cur_month = d.strftime('%m')
    cur_year  = d.strftime('%Y')
    key_name = '%s-aws-billing-detailed-line-items-%s-%s.csv.zip' % (acct_id, cur_year, cur_month)

    bill_csv = get_bill(creds,bucket_name,key_name)

    if args['cloudfront']:
        return cloudfront_monthly_prediction(bill_csv)

