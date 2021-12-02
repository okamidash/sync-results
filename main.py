#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: okamidash | GH: okamidash

# Standard library
import os
import fnmatch
import re

# Dependencies
import plotly.graph_objects as go

#fig = go.Figure(data=go.Bar(y=[2, 3, 1]))
#fig.write_html('first_figure.html', auto_open=True)

def find_tests(pattern: str, path: str) -> dict:
    result = {}
    for root, dirs, files in os.walk(path):
        #result[root] = []
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                if result.get(root) == None:
                    result[root] = []
                result[root].append(os.path.join(root, name))

    return result

IOPS_regex = re.compile("(?=IOPS=).*(?<=,)")

def parse_fio(fio_result: str) -> dict:
    for line in open(fio_result,'r'):
        print(IOPS_regex.search(line))
    

raw_fio_results = find_tests("FIO*.txt","raw")
etcd_results = find_tests("ETCD*.txt","raw")

fio_results = {}
for drive_name in raw_fio_results:
    fio_results[drive_name] = [parse_fio(raw_fio_result) for raw_fio_result in raw_fio_results[drive_name]]
   