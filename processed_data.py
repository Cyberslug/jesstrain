   #!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : processed_data.py
# @Version : 0.0
# @Date : 2019-10-20-14-50
# @Project: jesstrain
# @AUTHOR : david & jessir

class ProcessedData:
    """
    Holds all pre-processed data
    """
    class_var1 = 1  # define class vars here

    def __init__(self, directory):  # use **kwargs? if so how to put out relevant ones?
        self.directory = directory
        self._get_data()
        self._match_solutions_to_truth()
        self._get_PE()

    def _get_data(self):  # do i need to pass in directory here? or does it come with self? N
        print('Got {}'.format(self.directory))

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
# if called after the instances are instantiated
# Can call class vars for instance and will inherit from class. BUT if change the class var for that instance, will set
# the var with that instance and won't inherit the one from class

if __name__ == '__main__':
    fred = ProcessedData("Folder1")
    fred.__repr__()


