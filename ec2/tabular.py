"""
super simple utitities to display tabular data

columns is a list of tuples:

    - name: header name for the column
    - f: a function which takes one argument *row* and returns the value to
      display for a cell. the function which be called for each of the rows
      supplied
"""

import sys
import csv


def pcsv(columns, rows, key=lambda x: x):
    writer = csv.writer(sys.stdout)
    writer.writerow([x for x, _ in columns])
    for row in sorted(rows, key=key):
        writer.writerow([f(row) for _, f in columns])


def pprint(columns, rows, key=lambda x: x):
    lengths = {}

    for name, _ in columns:
        lengths[name] = len(name) + 1

    for row in rows:
        for name, f in columns:
            lengths[name] = max(lengths[name], len(str(f(row)))+1)

    fmt = ' '.join(['{:<%s}' % lengths[x] for x, _ in columns])
    print fmt.format(*[x for x, _ in columns])

    for row in sorted(rows, key=key):
        print fmt.format(*[f(row) for _, f in columns])
