#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: okamidash | GH: okamidash

# Standard library
import os
import fnmatch
import re
from operator import itemgetter
# Dependencies
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

fig = go.Figure(data=go.Bar(y=[2, 3, 1]))
# fig.write_html('first_figure.html', auto_open=True)


def find_tests(pattern: str, path: str) -> dict:
    """find_tests
    """
    result = {}
    for root, dirs, files in os.walk(path):
        # result[root] = []
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                if result.get(root) is None:
                    result[root] = []
                result[root].append(os.path.join(root, name))

    return result


IOPS_regex = re.compile("(?=IOPS=).*(?<=,)")
percentile_regex = re.compile("\d+\.?\d+th")
value_regex = re.compile("\d+")
unit_regex = re.compile("\(.*?\)")

def find_timings(lines: list, start: str, end: str):
    # Basic Dict to find percentile
    timings = {}
    # Iterate over each line
    for line_number,line in enumerate(lines):
        # If the line starts with the 'start string'
        if line.startswith(start):
            # Find the Unit
            unit = line[line.find("(")+1:line.find(")")]
         
            # Iterate over line_number + 1, to the end
            for clat_line in lines[line_number+1:]:
                # If we've reached the end of lines to split
                if clat_line.startswith(end):
                    return timings
                else:
                    percentiles = clat_line.split(',')
                    for indi_percentile in percentiles:
                        # Since ',' is on the end, continue to the next loop
                        if indi_percentile == '':
                            continue

                        # Find the percentile 
                        percentile = percentile_regex.search(indi_percentile)
                        # Split on = and match digits
                        percentile_value = value_regex.search(indi_percentile.split('=')[1])
                        # Convert between values to usec
                        if unit == "usec":
                            # We want usec
                            final_value = int(percentile_value.group())
                        elif unit == "nsec":    
                            final_value = int(percentile_value.group()) / 1000
                        elif unit == "msec":
                            final_value = int(percentile_value.group()) * 1000
                            
                        # Python 3.10 has case select
                        timings[percentile.group()] = final_value

def parse_fio(fio_result: str) -> dict:
    """parse_fio
    """
    lines = [line.strip() for line in open(fio_result, 'r')]
    # Inefficient, but easy to write
    clat_timings = find_timings(lines, "clat percentiles", "bw")
    sync_timings = find_timings(lines, "sync percentiles", "cpu")
   
    # print(clat_timings)
    print(sync_timings)
    #print(clat_timings)
    return sync_timings

def to_df(fio_results: dict) -> pd.DataFrame:
    data = {}
    rows = [x[4:] for x in fio_results.keys()]
    for fio_result in fio_results:
        data[fio_result[4:]] = fio_results[fio_result]
        averages = {}
        for percentile in fio_results[fio_result][0].keys():
            totals = list(map(itemgetter(percentile), fio_results[fio_result]))
            averages[percentile] = sum(totals)/len(totals)
            
        data[fio_result[4:]] = averages
        # for percentile in result[0].keys():
        #     percentile_results = [x[percentile] for x in result]
        #     average = round(sum(percentile_results)/len(percentile_results),5)

        #     if data.get(percentile) is None:
        #         data[percentile] = [average]
        #     else:
        #         data[percentile].append(average)
            
    
    #print(results)
    df = pd.DataFrame.from_dict(
    {
       
        **data
    }
    )
    #df.index = rows

    print(df.head())
    return df

raw_fio_results = find_tests("FIO*.txt", "raw")
etcd_results = find_tests("ETCD*.txt", "raw")

fio_results = {}
for drive in raw_fio_results:
    print(drive)
    fio_results[drive] = [parse_fio(rfw) for rfw in raw_fio_results[drive]]

fio_latency = to_df(fio_results)
fio_latency_figure = px.line(fio_latency, log_y=True, template="plotly_dark")
fio_latency_figure.update_layout(
    xaxis_title="Sync Percentiles",
    yaxis_title="Latency (usec)",
    legend_title="Drive",
)
fio_latency_figure.write_html('public/fio_latency_figure.html', auto_open=True)
