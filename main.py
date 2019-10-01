#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : main
# @Version : 0.0
# @Date : 2019-10-01-11-13
# @Project: jesstrain
# @AUTHOR : david
from os import listdir
from os.path import isfile, join


class Experiment:
    '''
    Holds all data relating to a specific experiment instance
    Note: Placeholder only
    '''
    def __init__(self, **kwargs):
        pass


class Analysis:
    '''
    Conducts analysis across multiple Experiment instance and displays the result
    Note: Placeholder only
    '''
    def __init__(self, experiments, **kwargs):
        pass

    def output(self):
        pass


def run():
    '''
    Main function
    Note: This is indicative only, code has not been tested
    '''
    repository_root = '//Team 17'  # indicate which data are to be processed here
    repositories = [f for f in listdir(repository_root) if not isfile(join(repository_root, f))]
    experiments = []
    for data in repositories:
        experiments.append(Experiment(directory=data, type='normal'))
    results = Analysis(experiments, type='normal')
    results.output()


if __name__ == '__main__':
    run()
