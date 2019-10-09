#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : analysis_tools.py
# @Version : 0.0
# @Date : 2019-04-13-17-57
# @Project: jesstrain
# @AUTHOR
# : david & jessir
"""
Functions for use with CRUSE data analysis
"""
from numpy import linalg


def bearingError(b1, b2):
    """Calculates the difference between 2 bearings in degrees"""
    r = abs((b2 % 360.) - (b1 % 360.))
    if r >= 180.0:
        r = 360.0 - r
    return r


def positionError(x1, x2, y1, y2):
    """Euclidean distance between 2 points"""
    pe = linalg.norm([(x1 - x2), (y1 - y2)])
    # pe = sqrt((x1-x2)**2 + (y1-y2)**2)
    return pe


def get_sec(time_str):
    """Convert time string in format 'HH:MM:SS' to seconds"""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)


if __name__ == '__main__':
    '''Example test code - this is overkill but hey'''
    assert (bearingError(360, 1) == 1.0)  # Test difference > 180
    assert (bearingError(361, 0) == 1.0)  # Test any angle
    assert (bearingError(0., 0.11) == 0.11)  # Test floating point
    assert (positionError(1, 0, 0, 0) == 1)  # Basic coordinate test
    assert (positionError(0, 1, 0, 0) == 1)  # Basic coordinate test
    assert (positionError(0, 0, 1, 0) == 1)  # Basic coordinate test
    assert (positionError(0, 0, 0, 1) == 1)  # Basic coordinate test
    assert (get_sec('00:00:01') == 1)
    assert (get_sec('00:01:00') == 60)
    assert (get_sec('01:00:00') == 3600)
    assert (get_sec('03:01:06') == 10866)
