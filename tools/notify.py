#!/usr/bin/python

from settings import hermes, arg, rprint

msg = arg(1, "I'm great achtung-daemon Hermes!")
rprint(hermes.notify([msg, "<div style='background-color:red'>"+msg+"</div>"],["error"]))
