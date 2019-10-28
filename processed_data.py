   #!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : processed_data.py
# @Version : 0.0
# @Date : 2019-10-20-14-50
# @Project: jesstrain
# @AUTHOR : david & jessir

from os import chdir, getcwd, path
from glob import glob
import pandas as pd

class ProcessedData:
    """
    Holds all pre-processed data
    """
    class_var1 = 1  # define class vars here
    data_directory = 'C:\\Users\\jesir\\PycharmProjects\\data'  # Name of the main data directory. Not sure where to put this yet - init?

    def __init__(self, **kwargs):  # Allow options for input by team/session or bya single output folder
        print(kwargs)
        self.team = kwargs.get('team', 'none')
        self.session = kwargs.get('session', 'none')
        self.directory = kwargs.get('directory', 'none')

        if (self.team != 'none') and (self.session != 'none'):
            self._get_data_by_team()
        elif self.directory != 'none':
            self._get_data_by_directory()
        else:
            print('Please enter the team and session or the directory')  # Work out how to do this as an exception

        self._match_solutions_to_truth()
        self._get_PE()

    def _get_data_by_team(self):
        chdir(self.data_directory + '\\Team ' + str(self.team))
        session_folder = glob('cruse-*')[self.session - 1]
        print(session_folder)
        self.directory = (self.data_directory + '\\Team ' + str(self.team) + '\\' + session_folder)
        chdir(self.directory)
        self.solution_legs = pd.read_csv('solution_legs.csv')  # TMA solutions
        self.ground_truth = pd.read_csv('target_solution.csv')  # Ground truth for each vessel every 20s
        self.ownship = pd.read_csv('navdata.csv')  # Ownship navigation data. Updated every 1s

    def _get_data_by_directory(self):
        chdir(self.data_directory)
        chdir(self.directory)
        self.team = 999  # Dummy number for team
        self.session = 1
        self.solution_legs = pd.read_csv('solution_legs.csv')  # TMA solutions
        self.ground_truth = pd.read_csv('target_solution.csv')  # Ground truth for each vessel every 20s
        self.ownship = pd.read_csv('navdata.csv')  # Ownship navigation data. Updated every 1s

    def _match_solutions_to_truth(self):
        self.matched_solution = self.class_var1 + 1
        return self.matched_solution  # Use self. or classname. to call class vars. BUT can change var within instance,
        # so need to know whether to use self. or class.

    def _get_PE(self):
        pass

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
# if called after the instances are instantiateds
# Can call class vars for instance and will inherit from class. BUT if change the class var for that instance, will set
# the var with that instance and won't inherit the one from class

if __name__ == '__main__':
    fred = ProcessedData(directory='cruse-20190520-131452')
    fred.__repr__()


