# -*- coding: utf-8 -*-
"""
Created on Sat Apr 13 17:57:37 2019

Functions for use with CRUSE data analysis

NEED TO WORK OUT HOW TO IMPORT

@author: jesir
"""

# Calculates the difference between 2 true bearings
def bearingError(b1, b2):
    r = abs(b2 - b1)
    if r >= 180.0:
        r = 360.0 - r
    return r

def positionError(x1, x2, y1, y2):
    pe = np.sqrt((x1-x2)**2 + (y1-y2)**2)
    return pe        

# Convert time to seconds
def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

print('done')