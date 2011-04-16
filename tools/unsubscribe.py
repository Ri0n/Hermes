#!/usr/bin/python

from settings import hermes, arg, rprint, executer

def do():
    ret = hermes.unsubscribe(arg(1), arg(2))
    rprint(ret)

def syntax():
    return __file__ + " addressType address"

def example():
    return __file__ + " XMPP user@jabber.org"

executer(do, syntax, example)
