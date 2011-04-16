#! /usr/bin/python
from __future__ import absolute_import

__author__="rion"
__date__ ="$11.02.2010 12:40:23$"

from optparse import OptionParser
from hermes.hermes_core import HermesCore

def main(configFile = "/etc/hermes.xml"):
    usage = "usage: %prog [options]"
    parser = OptionParser(usage)
    parser.add_option("-c", "--config", dest="configFile", metavar="FILENAME",
                      help="read config from FILENAME")
    (options, args) = parser.parse_args()
    configFile = options.configFile or configFile
    app = HermesCore(configFile)
    app.run()


if __name__ == "__main__":
    main()
