#!/usr/bin/python

from settings import hermes, arg, rprint, executer

def do():
    ret = hermes.directNotify(arg(1), [[arg(2), arg(3, 'XMPP')]])
    rprint(ret)

def syntax():
    return __file__ + " message address [addressType=XMPP]"

def example():
    return __file__ + " \"This is a message\" user@jabber.org XMPP"

executer(do, syntax, example)
