#!/usr/bin/python

from settings import hermes, arg, rprint, executer

def do():
    priv = arg(4, None)
    if priv:
        ret = hermes.subscribe(arg(1), arg(2), arg(3), priv)
    else:
        ret = hermes.subscribe(arg(1), arg(2), arg(3))
    rprint(ret)

def syntax():
    return __file__ + " addressType address subscription[ privilege=USER]"

def example():
    return __file__ + " XMPP user@jabber.org '*' ADMIN"

executer(do, syntax, example)
