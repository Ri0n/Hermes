# To change this template, choose Tools | Templates
# and open the template in the editor.
from twisted.web import server
from twisted.internet import reactor
from twisted.internet.ssl import DefaultOpenSSLContextFactory

from rcore.xmlrpc import Site, XMLRPC
from rcore.core import Core
from rcore.config import config
from hermes import contacts


def init():
    if int(config().demon._get("ssl", 0)):
        reactor.listenSSL(
            int(config().demon.port),
            HermesSite(),
            DefaultOpenSSLContextFactory(
                config().ssl.private,
                config().ssl.cert
            ),
            interface=config().demon._get("if","127.0.0.1")
        )
    else:
        reactor.listenTCP(
            int(config().demon.port),
            HermesSite(),
            interface=config().demon._get("if","127.0.0.1")
        )

class HermesSite(Site):

    def __init__(self, logPath=None, timeout=60 * 60 * 12):
        root = HermesResource(allowNone=True)
        server.Site.__init__(self, root, logPath, timeout)


class HermesResource(XMLRPC):
    """HERMES Request demon"""

    def auth(self, user, passwd):
        c = config().demon
        return Core.instance().auth(user, passwd)

    def xmlrpc_notify(self, message, tags=[]):
        Core.instance().notify(message, tags)
        return True
    
    def xmlrpc_notifyAll(self, message):
        Core.instance().notifyAll(message)
        return True
    
    def xmlrpc_directNotify(self, message, recipients):
        recipients = [contacts.Contact.fromDict(dict(address=r[1],type=contacts.__dict__["AT_"+r[0]])) #@UndefinedVariable
                      for r in recipients]
        return Core.instance().directNotify(message, recipients)
    
    def xmlrpc_getContacts(self):
        return [c.toDict() for c in Core.instance().getContacts()]
    
    def xmlrpc_subscribe(self, addressType, address, subscription="", privilege="USER"):
        addressType = contacts.__dict__["AT_"+addressType] #@UndefinedVariable
        privilege = contacts.__dict__["PRIV_"+privilege] #@UndefinedVariable
        return Core.instance().subscribe(addressType, address, subscription, privilege).toDict()
    
    def xmlrpc_unsubscribe(self, addressType, address):
        addressType = contacts.__dict__["AT_"+addressType] #@UndefinedVariable
        return Core.instance().unsubscribe(addressType, address)
