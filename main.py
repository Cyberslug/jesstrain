#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : main
# @Version : 0.0
# @Date : 2019-10-01-11-13
# @Project: jesstrain
# @AUTHOR : david & jessir
from os import listdir
from os.path import isfile, join
from experiment import Experiment




def run():
    '''
    Main function
    Note: This is indicative only, code has not been tested
    '''
    repository_root = 'Team 17//'  # indicate which data are to be processed here
    repositories = [f for f in listdir(repository_root) if not isfile(join(repository_root, f))]  # only directories
    experiments = []
    #  processed_data = []  # Note that this is not necessary as the processed data exists in the class instance
    for data in repositories:
        experiments.append(Experiment(directory=data, type='normal'))


if __name__ == '__main__':
    run()
