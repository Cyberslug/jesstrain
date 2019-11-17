   #!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : processed_data.py
# @Version : 0.0
# @Date : 2019-10-20-14-50
# @Project: jesstrain
# @AUTHOR : david & jessir

from os import chdir
from glob import glob
import pandas as pd
import numpy as np
import constants
from analysis_tools import bearingError
import warnings
from sys import exit

class ProcessedData:
    """
    Holds all pre-processed data
    """
    class_var1 = 1  # define class vars here
    # TODO work out where to put these below. Contants.py?
    data_directory = 'C:\\Users\\jesir\\PycharmProjects\\data'  # Name of the main data directory
    chdir(data_directory)
    sonar_start_times = pd.read_csv('Sonar_start_time.csv')  # time each contact visual on sonar

    def __init__(self, **kwargs):  # Allow options for input by team/session or bya single output folder
        print(kwargs)
        self.team = kwargs.get('team', 'none')
        self.session = kwargs.get('session', 'none')
        self.directory = kwargs.get('directory', 'none')

        if self.directory == 'none':
            self._get_directory_name()
        if self.team != 'none':
            self.team = 999
            self.session = 999

        self._get_raw_data()
        self._clean_solution_legs()
        self._match_solutions_to_truth()
        self._get_position_error()

    def _get_directory_name(self):
        try:
            chdir(self.data_directory + '\\Team ' + str(self.team))
            session_folder = glob('cruse-*')[self.session - 1]
            print(session_folder)
            self.directory = (self.data_directory + '\\Team ' + str(self.team) + '\\' + session_folder)
        except FileNotFoundError:
            missing_input_error = 'Please include the team + session number or the data folder name as input'
            warnings.warn(missing_input_error)
            exit()

    def _get_raw_data(self):
        chdir(self.data_directory)
        chdir(self.directory)
        self.solution_legs = pd.read_csv('solution_legs.csv')  # TMA solutions
        self.ground_truth = pd.read_csv('target_solution.csv')  # Ground truth for each vessel every 20s
        self.ownship = pd.read_csv('navdata.csv')  # Ownship navigation data. Updated every 1s

    def _clean_solution_legs(self):
        # Some of this is likely to be specific to individual experiments
        # Remove visual solutions initiated by TPC
        self.solution_legs = self.solution_legs[self.solution_legs.sl_console != 'TPC'].copy()
        # Convert to same units as ground truth (yds, kts)
        self.solution_legs.loc[:, 'sl_range'] = self.solution_legs.loc[:, 'sl_range'] * constants.m2yd
        self.solution_legs.loc[:, 'sl_speed'] = self.solution_legs.loc[:, 'sl_speed'] * constants.mps2kt
        # Get ownship x/y from Navdata for the time each SL was lodged
        for sl, row in self.solution_legs.iterrows():
            own_criteria = (self.ownship.loc[:, 'nd_time'] == round(self.solution_legs.loc[sl, 'sl_time']))
            self.solution_legs.loc[sl, 'sl_ownship_x'] = self.ownship[own_criteria].iloc[0]['nd_x']
            self.solution_legs.loc[sl, 'sl_ownship_y'] = self.ownship[own_criteria].iloc[0]['nd_y']
        # Calculate x/y of each solution using bearing and range
        self.solution_legs.loc[:, 'sl_x'] = self.solution_legs['sl_range'] * \
                                            np.sin(np.deg2rad((self.solution_legs['sl_bearing']))) + \
                                            self.solution_legs['sl_ownship_x']
        self.solution_legs.loc[:, 'sl_y'] = self.solution_legs['sl_range'] * \
                                            np.cos(np.deg2rad((self.solution_legs['sl_bearing']))) + \
                                            self.solution_legs['sl_ownship_y']

    def _match_solutions_to_truth(self):

        solution_ids = pd.unique(self.solution_legs['sl_sid'])
        # Find closest ground truth
        for solution_id in solution_ids:
            solution_criteria = (self.solution_legs['sl_sid'] == solution_id)
            solution_bearing = self.solution_legs[solution_criteria].iloc[0]['sl_bearing']  # First solution/contact
            solution_time = self.solution_legs[solution_criteria].iloc[0]['sl_time']
            recent_timepoint = np.floor(solution_time / 20) * 20  # Most recent 20sec timepoint
            # limit to only those truth_ids that are within sonar range (sort because sonar_start_time not sorted)
            visible_truth_ids = sorted(self.sonar_start_times.loc[(self.sonar_start_times['Time']) <= solution_time]['Con'])
            search_criteria = (self.ground_truth['ts_time'] == recent_timepoint) & \
                              (self.ground_truth['ts_id'].isin(visible_truth_ids))
            # Find the difference in bearing between solution and each ground truth
            bearing_differences = [bearingError(bearing, solution_bearing)
                                      for bearing in self.ground_truth[search_criteria]['ts_bearing']]
            # Find the truth ID of the vessel with the minimum bearing difference
            truth_id = visible_truth_ids[bearing_differences.index(min(bearing_differences))]
            # Update in solutions legs data frams
            self.solution_legs.loc[solution_criteria, 'sl_truth_id'] = truth_id

            # Flag anything weird going on here
            if min(bearing_differences) > 1:
                bearing_error_warning = ('Solution ' + str(solution_id) + ' assigned to truth contact ' + str(truth_id)
                                         + ' with large bearing error of ' + str(round(min(bearing_differences), 1)))
                warnings.warn(bearing_error_warning)
            if len([b for b in bearing_differences if b <= 1]) > 1:  # Check if multiples truths within 1 degree
                index_list = [i for i, value in enumerate(bearing_differences) if value < 1]
                multiple_contacts_warning = ('Solution ' + str(solution_id) + ' within 1 degree of multiple contacts at'
                                             + ' time of assignment. Assigned to truth contact ' + str(truth_id)
                                             + ' but close to ' + str([visible_truth_ids[i] for i in index_list]))
                warnings.warn(multiple_contacts_warning)


    def _get_position_error(self):
        for sl, sl_row in self.solution_legs.iterrows():
            truth_id = sl_row['sl_truth_id']
            solution_time = sl_row['sl_time']
            solution_x, solution_y = sl_row['sl_x'], sl_row['sl_y']
            # Find the x/y coordinates of the exact solution timepoint (extrapolate from bearing cuts
            # TODO make this a separate method? if used more than here
            last_timepoint = np.floor(solution_time / constants.timepoint_secs) * constants.timepoint_secs
            next_timepoint = np.ceil(solution_time / constants.timepoint_secs) * constants.timepoint_secs
            truth_criteria = (self.ground_truth['ts_id'] == truth_id) & \
                                                    (self.ground_truth['ts_time'] >= last_timepoint) & \
                                                    (self.ground_truth['ts_time'] <= next_timepoint)
            last_x, last_y = self.ground_truth[truth_criteria].iloc[0]['ts_x'], \
                                                    self.ground_truth[truth_criteria].iloc[0]['ts_y']
            next_x, next_y = self.ground_truth[truth_criteria].iloc[-1]['ts_x'], \
                                                    self.ground_truth[truth_criteria].iloc[-1]['ts_y']
            truth_x = last_x + (next_x - last_x) * (solution_time - last_timepoint) / constants.timepoint_secs
            truth_y = last_y + (next_y - last_y) * (solution_time - last_timepoint) / constants.timepoint_secs

            # TODO possibly make position error function if use more than here.
            self.solution_legs.loc[sl, 'Position Error'] = np.linalg.norm([(truth_x - solution_x),
                                                                       (truth_y - solution_y)])



    # Playing around with other things:
    @property  # Defined like property but acts like attribute. Allows var to be updated after init
    def set_property(self):
        pass

    def __repr__(self):  # Call with instance.__repr__()
        return 'Directory {}'.format(self.directory)

    def __str__(self):
        return 'Analysing data from {}'.format(self.directory)


    @classmethod  # Method applied to entire class - might be useful if need to upload constant to entire class...?
    def do_class_method(cls):
        cls.class_var1 = 3

    @staticmethod  # Doesn't take class or instance as argument
    def do_static_method():
        pass


# print(instance.__dict__) shows the instance vars
# print(Class.__dict__) shows the class vars
# Can change class var for the entire class (e.g. ProcessedData.class_var1 = 2) and will change for all instance, even
# if called after the instances are instantiated
# Can call class vars for instance and will inherit from class. BUT if change the class var for that instance, will set
# the var with that instance and won't inherit the one from class

if __name__ == '__main__':
    fred = ProcessedData(directory='cruse-20190520-131452')
    #fred = ProcessedData()
    #fred.solution_legs.to_csv('test_sl_output.csv')
    fred.__repr__()


