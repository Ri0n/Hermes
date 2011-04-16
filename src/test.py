#!/usr/bin/python

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os

from hermes.main import main
main(os.path.join(os.path.dirname(__file__), "../config.xml"))
