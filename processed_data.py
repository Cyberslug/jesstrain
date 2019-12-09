   #!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : processed_data.py
# @Version : 0.0
# @Date : 2019-11-24-10-02
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
        self._get_response_time()
        self.process_sonar_data()

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
        self.sonar = pd.read_csv('sonar_tracks.csv')  # Sonar tracks data
        self.user_interactions = pd.read_csv('user_interactions.csv')  # User interactions by each operator.

        self.consoles = pd.unique(self.user_interactions['ui_hmi'])
        self.consoles.sort()

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
            self.solution_legs.loc[sl, 'Range Error'] = abs(self.ground_truth[truth_criteria].iloc[0]['ts_range'] -
                                                        sl_row['sl_range'])
            self.solution_legs.loc[sl, 'Speed Error'] = abs(self.ground_truth[truth_criteria].iloc[0]['ts_speed'] -
                                                        sl_row['sl_speed'])
            self.solution_legs.loc[sl, 'Course Error'] = bearingError(
                                                        self.ground_truth[truth_criteria].iloc[0]['ts_course'],
                                                        sl_row['sl_course'])

    def _get_response_time(self):
         # TODO get rid of outliers?
        truth_ids = pd.unique(self.ground_truth['ts_id'])
        no_sonar_subset = (self.solution_legs['sl_console'].str.contains("TMA")) # Focus on TMA solutions only
        # For each contact, get the time taken to update solution on that contact
        for truth_id in truth_ids:
            truth_id_subset = (self.solution_legs['sl_truth_id'] == truth_id)
            sierra_initiated_time = self.solution_legs[truth_id_subset].iloc[0]['sl_time']
            # If TMA solutions exist
            if self.solution_legs[truth_id_subset & no_sonar_subset].shape[0] > 0:
                solution_times = self.solution_legs.loc[truth_id_subset & no_sonar_subset]['sl_time'].tolist()
                solution_times.insert(0, sierra_initiated_time)
                # subtract each time from previous solution time
                update_rts = [x - y for x, y in zip(solution_times[1:], solution_times)]
                self.solution_legs.loc[truth_id_subset & no_sonar_subset, 'sl_update_RT'] = update_rts
                # Count number updates
                self.solution_legs.loc[truth_id_subset & no_sonar_subset, 'sl_update_count'] = \
                    range(1, len(update_rts) + 1)
        # RT for each TMA operator
        tma_count = sum('TMA' in console for console in self.consoles)  # Count how many TMAs
        for tma in range(1,tma_count+1):
            tma_subset = (self.solution_legs['sl_console'].str.contains('TMA' + str(tma)))
            if self.solution_legs[tma_subset].shape[0] > 1: # Must be more than 1 solution
                tma_times = self.solution_legs.loc[tma_subset]['sl_time'].tolist()
                tma_rts = [x - y for x, y in zip(tma_times[1:], tma_times)]
                tma_rts.insert(0, np.nan)
                self.solution_legs.loc[tma_subset, 'sl_TMA_RT'] = tma_rts

    # Don't make this one obligatory?
    def _process_sonar_data(self):
        truth_ids = pd.unique(self.ground_truth['ts_id'])
        # Find closest ground truth
        for truth_id in truth_ids:
            sonar_subset = (self.sonar['st_entity_id'] == truth_id)
            solution_subset = (self.solution_legs['sl_truth_id'] == truth_id)
            # Find time that tracker ID initiated
            if self.solution_legs.loc[solution_subset].shape[0] > 0:  # If any TIDs assigned
                self.solution_legs.loc[solution_subset, 'sl_sonar_detect_time'] = \
                    self.sonar[sonar_subset].iloc[0]['st_init_time']
                # Choose the time of the first TID
                self.solution_legs.loc[solution_subset, 'sl_sierra_initiated_time'] = \
                    self.solution_legs[solution_subset].iloc[0]['sl_time']


if __name__ == '__main__':
    #fred = ProcessedData(directory='TMAonly')
    jan = ProcessedData(team=17, session=1)
    #print(jan.solution_legs.head())
    #pass
    #fred = ProcessedData()
    jan.solution_legs.to_csv('test_sl_output.csv')


