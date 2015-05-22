__version__     = "0.0.5"
__author__      = "Job Snijders, Peter van Dijk"
__author_email__ = "job@instituut.net"
__copyright__   = "Copyright 2015, Job Snijders & Peter van Dijk"
__license__     = "BSD 2-Clause"
__status__      = "Development"
__url__         = "https://github.com/job/irrexplorer"

import yaml

class config(object):
    """config stub object for nrtm testing"""
    def __init__(self, cfgfile):
        data = yaml.load(open(cfgfile))
        self.databases = data['databases']

