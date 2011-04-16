# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding('utf-8') #@UndefinedVariable

from pprint import PrettyPrinter
import xmlrpclib

url='https://guest:guest@localhost:9876'
hermes = xmlrpclib.Server(url, allow_none = True)

def executer(func, syntax, example):
    def printHelp():
        syntaxStr = syntax() if callable(syntax) else "[not given]"
        exampleStr = example() if callable(example) else "[not given]"
        print '''
\033[1;37mProper syntax for this command:\033[1;m
  \033[1;32m$\033[1;m \033[1;36m%s\033[1;m
\033[1;37mExample:\033[1;m
  \033[1;32m$\033[1;m \033[1;36m%s\033[1;m''' % (syntaxStr, exampleStr)
    
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        printHelp()
        return
        
    try:
        func()
    except:
        print '\033[1;31mSomething went wrong:'
        traceback.print_exc()
        print '\033[1;m'
        printHelp()

def arg(num, default = None):
    return sys.argv[num] if len(sys.argv) > num else default

class MyPrettyPrinter(PrettyPrinter):
    def format(self, *args, **kwargs):
        repr, readable, recursive = PrettyPrinter.format(self, *args, **kwargs)
        if repr:
            if repr[0] in ('"', "'"):
                repr = repr.decode('string_escape')
            elif repr[0:2] in ("u'", 'u"'):
                repr = repr.decode('unicode_escape').encode(sys.stdout.encoding)
        return repr, readable, recursive

def rprint(obj, stream=None, indent=1, width=80, depth=None):
    printer = MyPrettyPrinter(stream=stream, indent=indent, width=width, depth=depth)
    printer.pprint(obj)
