#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: okamidash | GH: okamidash

# Standard library
import os
import fnmatch
import re
from operator import itemgetter
from collections import Counter
# Dependencies
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

# Locale mangling
import locale
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

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

def parse_fio(fio_result_path: str) -> dict:
    """parse_fio
    """
    lines = [line.strip() for line in open(fio_result_path, 'r')]
    # Inefficient, but easy to write
    clat_timings = find_timings(lines, "clat percentiles", "bw")
    sync_timings = find_timings(lines, "sync percentiles", "cpu")
    return sync_timings

def parse_etcd(etcd_result_path: str) -> dict:
    lines = [line.strip() for line in open(etcd_result_path, 'r')]
    timings = {}
    in_results = False
    for line in lines:
        if line == "Latency distribution:":
            in_results = True
        # Evalute this before adding the result, so we don't add the last result
        elif line == '' and in_results:
            return timings
        elif in_results:
            split_line = line.split(' ')
            percentile = split_line[0]
            value = float(split_line[2]) * 1000
            timings[percentile] = value

def cs_to_int(comma_separated_string: str) -> int:
    return locale.atoi(comma_separated_string)

def parse_ceph(ceph_result_path: str) -> dict:
    lines = [line.strip() for line in open(ceph_result_path, 'r')]
    in_results = False
    results = {}
    for line in lines:
        if line == "IOPS (Read/Write)":
            resultset = "IOPS"
            in_results = True
        elif line == "Bandwidth in KiB/sec (Read/Write)":
            resultset = "BW"
            in_results = True
        elif line == "Latency in ns (Read/Write)":
            resultset = "LAT"
            in_results = True
        # Evalute this before adding the result, so we don't add the last result
        elif line == '' and in_results:
            in_results = False
        elif in_results is True:
            split_line = line.split(' ')
            if results.get("random") is None:
                results["random"] = {}
            elif results.get("sequential") is None:
                results["sequential"] = {}

            metric = split_line[0]
            if metric == "Random:":
                results["random"][resultset] = {
                    "read": cs_to_int(split_line[-3]),
                    "write": cs_to_int(split_line[-1])
                }

            elif metric == "Sequential:":
                results["sequential"][resultset] = {
                    "read": cs_to_int(split_line[-3]),
                    "write": cs_to_int(split_line[-1])
                }


    return results

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
  
            
    df = pd.DataFrame.from_dict(
    {
       
        **data
    }
    )
    return df

raw_fio_results = find_tests("FIO*.txt", "raw")
raw_etcd_results = find_tests("ETCD*.txt", "raw")
raw_ceph_results = {
    4: {

        1: find_tests("CEPH-REPLICA1-4OSD*.txt", "raw"),
        3: find_tests("CEPH-REPLICA3-4OSD*.txt", "raw")
    },
    5: {
        1: find_tests("CEPH-REPLICA1-5OSD*.txt", "raw"),
        3: find_tests("CEPH-REPLICA3-5OSD*.txt", "raw")
    }
   
}



drives = raw_fio_results.keys()
fio_results = {}
etcd_results = {}
ceph_results = {}
for drive in drives:
    fio_results[drive] = [parse_fio(rfw) for rfw in raw_fio_results[drive]]
    etcd_results[drive] = [parse_etcd(rfw) for rfw in raw_etcd_results[drive]]
    ceph_results[drive] = {
        4: {
            1: [parse_ceph(rfw) for rfw in raw_ceph_results[4][1][drive]][0],
            3: [parse_ceph(rfw) for rfw in raw_ceph_results[4][3][drive]][0]
        },
        5: {
            1: [parse_ceph(rfw) for rfw in raw_ceph_results[5][1][drive]][0],
            3: [parse_ceph(rfw) for rfw in raw_ceph_results[5][3][drive]][0]
        }
    }

# Do some extra special mangling to the ceph data so that pandas can work with it properly
# The aim is to create a table that looks roughly like this
#   Drive                       REPLICAS    OSDS    METRIC      IOPS (R)    IOPS (W)    Bandwidth (R) Bandwitch (W) Latency (R)   Latency(W)
#   SAMSUNG MZ1WV480HCGL-000MV  1           4       RANDOM      7624        4676        722774        462495        2812625       6605905
#   SAMSUNG MZ1WV480HCGL-000MV  1           4       SEQUENTIAL  7624        4676        722774        462495        2812625       6605905
#   SAMSUNG MZ1WV480HCGL-000MV  3           4       RANDOM      7624        4676        722774        462495        2812625       6605905
#   SAMSUNG MZ1WV480HCGL-000MV  3           4       SEQUENTIAL  7624        4676        722774        462495        2812625       6605905
#   SAMSUNG MZ1WV480HCGL-000MV  1           4       RANDOM      7624        4676        722774        462495        2812625       6605905
#   SAMSUNG MZ1WV480HCGL-000MV  3           5       RANDOM      7624        4676        722774        462495        2812625       6605905
final = pd.DataFrame()
for drive in drives:
    drive_pretty = drive[4:]
    ceph_results[drive]
    for osd_count in ceph_results[drive]:
        for replica_count in ceph_results[drive][osd_count]:
            result = ceph_results[drive][osd_count][replica_count]
            rand_result = result['random']
            seq_result =  result['sequential']
            # Do it for Random, then sequential
            df =  [{
                    'drive': drive_pretty,
                    'replicas': replica_count,
                    'osds': osd_count,
                    'metric': 'random',
                    'rw':'read',
                    'IOPS':  rand_result['IOPS']['read'],
                    'Bandwidth': rand_result['BW']['read'],
                    'Latency': rand_result['LAT']['read'],
                },
                {
                    'drive': drive_pretty,
                    'replicas': replica_count,
                    'osds': osd_count,
                    'metric': 'random',
                    'rw':'write',
                    'IOPS':  rand_result['IOPS']['write'],
                    'Bandwidth': rand_result['BW']['write'],
                    'Latency': rand_result['LAT']['write'],
                },
                {
                    'drive': drive_pretty,
                    'replicas': replica_count,
                    'osds': osd_count,
                    'metric': 'sequential',
                    'rw':'read',
                    'IOPS':         seq_result['IOPS']['read'],
                    'Bandwidth':    seq_result['BW']['read'],
                    'Latency':      seq_result['LAT']['read'],
                },
                {
                    'drive': drive_pretty,
                    'replicas': replica_count,
                    'osds': osd_count,
                    'metric': 'sequential',
                    'rw':'write',
                    'IOPS':         seq_result['IOPS']['write'],
                    'Bandwidth':    seq_result['BW']['write'],
                    'Latency':      seq_result['LAT']['write'],
                }
            ]
            final = final.append(df)

#print(final.query('replicas == 1 and metric == "random" and rw =="write"').groupby(by='metric').head())

def find_data(final, replicas: int, osds: int, metric: str, rw: str, ):
    return final.query(f'replicas == {replicas} and metric == "{metric}" and rw =="{rw}" and osds == {osds}').sort_values(by='drive')

def mkset(final, rseq: str, rw: str) -> dict:
    r1osd4 = find_data(final, 1, 4, rseq, rw)
    r1osd5 = find_data(final, 1, 5, rseq, rw)
    r3osd4 = find_data(final, 3, 4, rseq, rw)
    r3osd5 = find_data(final, 3, 5, rseq, rw)
    return {
        'Replica 1, 4 OSD': r1osd4,
        'Replica 1, 5 OSD': r1osd5,
        'Replica 3, 4 OSD': r3osd4,
        'Replica 3, 5 OSD': r3osd5
    }


def create_figure(final, rseq: str, rw: str, metric: str, unit: str = ""):
    if unit is not "":
        unit = f" ({unit})"
    dataset = mkset(final, rseq, rw)
    data = []
    for name in dataset:
        dataset_indi = dataset[name]
        data.append(
            go.Bar(
                name=name,
                x=dataset_indi['drive'],
                y=dataset_indi[metric] 
            ),
        )
    
    figure = go.Figure(data=data)
    figure.update_layout(
    #xaxis_title="Drive",
    yaxis_title=f"{metric}{unit}",
    title=f"{metric.capitalize()} ({rseq.capitalize()} {rw}s)",
    barmode='group',
    legend_title="",
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="right",
        x=0.99
        )
    )
    
    figure.write_html(f'public/{rseq}_{rw}_{metric}.html')

# Create the bandwidth figures
bandwidth_unit = "KiB/sec"
# Sequential
create_figure(final, "sequential", "read",  "Bandwidth", bandwidth_unit)
create_figure(final, "sequential", "write", "Bandwidth", bandwidth_unit)
# Random
create_figure(final, "random", "read", "Bandwidth", bandwidth_unit)
create_figure(final, "random", "write", "Bandwidth", bandwidth_unit)

# Create the IOPS figures
# Sequential
create_figure(final, "sequential", "read",  "IOPS")
create_figure(final, "sequential", "write", "IOPS")
# Random
create_figure(final, "random", "read", "IOPS")
create_figure(final, "random", "write", "IOPS")

# Create the IOPS figures
latency_unit = "Microseconds"

# Sequential
create_figure(final, "sequential", "read",  "Latency", latency_unit)
create_figure(final, "sequential", "write", "Latency", latency_unit)
# Random
create_figure(final, "random", "read", "Latency", latency_unit)
create_figure(final, "random", "write", "Latency", latency_unit)







bar_chart = px.bar(
    final.query('replicas == 1 and metric == "random" and rw =="write"'), 
    x='drive', 
    y='Bandwidth', 
    
    facet_col="osds",
    barmode='group')
#bar_chart.write_html('public/bar.html', auto_open=True)

etcd_latency = to_df(etcd_results)
etcd_latency_figure = px.line(etcd_latency)
etcd_latency_figure.update_layout(
    xaxis_title="Sync Percentiles",
    yaxis_title="Latency (msec)",
    legend_title="Drive",
    legend=dict(
    yanchor="top",
    y=0.99,
    xanchor="left",
    x=0.01
    )
)
etcd_latency_figure.write_html('public/etcd.html')

fio_latency = to_df(fio_results)
fio_latency_figure = px.line(fio_latency, log_y=True)
#template="plotly_dark")
fio_latency_figure.update_layout(
    xaxis_title="Sync Percentiles",
    yaxis_title="Latency (usec)",
    legend_title="Drive",
    legend=dict(
    yanchor="top",
    y=0.99,
    xanchor="left",
    x=0.01
)
)
fio_latency_figure.write_html('public/fio.html')
