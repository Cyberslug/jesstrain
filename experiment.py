   #!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Filename : experiment.py
# @Version : 0.0
# @Date : 2019-10-02-08-36
# @Project: jesstrain
# @AUTHOR : david & jessir
# import
# I suggest that we do not increment the version number until we have a basic version entered and minimally functional
# Version 0 is typically the initial version and major versions (i.e. 0.x) indicate addition of significant features,
# minor versions (i.e. x.0) indicate fixes to existing functionality

class Session:
    """
    Holds all data relating to a specific experiment instance
    Note: Placeholder only
    """
    # NOTE: I decided to use **kwargs argument here as it was not clear the extent of arguments require
    def __init__(self, **kwargs):
        pass

    # NOTE: Your call as to where the processing happens.  In this class is probably best as it is unlikely to be
    # useful anywhere else. Note that this just returns the values on the fly, no need to store these.
    def process_data(self):
        pass

    def _load_data(self):
        """ Load data from a series of csv files"""
        pass



if __name__ == '__main__':
    pass
