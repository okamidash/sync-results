#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: okamidash | GH: okamidash

# Standard library
import os
import fnmatch

# Dependencies
import plotly.graph_objects as go

#fig = go.Figure(data=go.Bar(y=[2, 3, 1]))
#fig.write_html('first_figure.html', auto_open=True)

def find_tests(pattern: str, path: str) -> list:
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
    return result

def parse_fio():
    pass

print(find_tests("*.txt","raw"))