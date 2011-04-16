#!/usr/bin/env python

from distutils.core import setup
from distutils.dir_util import mkpath

dist = setup(
    name='hermes',
    version='0.1',
    description = "Notification daemon with various in/out interfaces",
    long_description = """This small python daemon written using
        twisted accepts messages using XML-RPC interface (and maybe some
        other in future and send them to one or more contacts via XMPP
        or some other service/protocol)""",
    author="rion",
    author_email="rion4ik@gmail.com",
    url="https://github.com/Ri0n/Hermes",
    license="GPL-3",

    package_dir={'':'src'},
    packages=['hermes'],
    py_modules=[],
    requires=["twisted.web", "twisted.names", "twisted.words"],

    scripts = ['hermes'],
    data_files=[
        ("/etc",["data/hermes.xml"])
    ]
)

