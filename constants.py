#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : constants
# @Version : 0.0
# @Date : 2019-09-04-12-23
# @Project: CRUSE
# @AUTHOR : david

yd2m = 0.9144
m2yd = 1.09361
mps2kt = 1.94384
kt2mps = 0.514444
kt2ypm = 33.7562  # (was ypm) Yards per minute travelling at 1 knot = 33.756

exclude_RT_outliers = True #set to 1 to exclude solutions that are made too quickly from last solution
exclude_sonar_outliers = True # set to 1 to exclude any solutions that set the range beyond what sonar can detect
exclude_bearing_outliers = True # set to 1 to exclude any solutions with bearing errors outside bearerrmax
endtime = 3700  # total number of seconds to look at
timepoint_secs = 20  # number of seconds per time point
timepoint_number = int(endtime / timepoint_secs)
points_range = .33  # Solution must be within this proportion of range in order # to score a point
zig_degrees = 30  # How many degrees change in course to qualify for a zig
sonar_range = 30000  # Max range for detection (as told to participants)
bearing_error_max = 20  # bearing errors outside of this considered outliers
minRT = 10  # minimum allowable time since last solution
# Weights from highest 3 to lowest 1 CLASSIFICATION BELOW
classification_weights_dict = {'Warship': 3, 'Fishing': 2, 'Merchant': 1}
range_weights_dict = {5000: 3, 10000: 2, 15000: 1}
course_weights_dict = {'Closing': 3, 'Opening': 1}
zig_weights_dict = {'Zigging': 3, 'Notzigging': 1}


exclude_RT_outliers = True #set to 1 to exclude solutions that are made too quickly from last solution
exclude_sonar_outliers = True # set to 1 to exclude any solutions that set the range beyond what sonar can detect
exclbearoutliers = True # set to 1 to exclude any solutions with bearing errors outside bearerrmax
endtime = 3700  # total number of seconds to look at
tpdur = 20  # number of seconds per time point
tpnum = int(endtime / tpdur)
ypm = 33.756  # Yards per minute travelling at 1 knot = 33.756
pointsrange = .33  # Solution must be within this proportion of range in order # to score a point
zigdegrees = 30  # How many degrees change in course to qualify for a zig
sonarrange = 30000  # Max range for detection (as told to participants)
bearerrmax = 20  # bearing errors outside of this considered outliers
minRT = 10  # minimum allowable time since last solution
# Weights from highest 3 to lowest 1 CLASSIFICATION BELOW
classification_weights_dict = {'Warship': 3, 'Fishing': 2, 'Merchant': 1}
rangeweightdict = {5000: 3, 10000: 2, 15000: 1}
courseweightdict = {'Closing': 3, 'Opening': 1}
zigweightdict = {'Zigging': 3, 'Notzigging': 1}
