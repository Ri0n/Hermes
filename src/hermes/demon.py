# To change this template, choose Tools | Templates
# and open the template in the editor.
from twisted.web import server
from twisted.internet import reactor
from twisted.internet.ssl import DefaultOpenSSLContextFactory

from rcore.xmlrpc import Site, XMLRPC
from rcore import getCore, config
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
        return getCore().auth(user, passwd)

    def xmlrpc_notify(self, message, tags=[]):
        getCore().notify(message, tags)
        return True
    
    def xmlrpc_notifyAll(self, message):
        getCore().notifyAll(message)
        return True
    
    def xmlrpc_directNotify(self, message, recipients):
        recipients = [contacts.Contact.fromDict(dict(address=r[1],type=contacts.__dict__["AT_"+r[0]])) #@UndefinedVariable
                      for r in recipients]
        return getCore().directNotify(message, recipients)
    
    def xmlrpc_getContacts(self):
        return [c.toDict() for c in getCore().getContacts()]
    
    def xmlrpc_subscribe(self, addressType, address, subscription="", privilege="USER"):
        addressType = contacts.__dict__["AT_"+addressType] #@UndefinedVariable
        privilege = contacts.__dict__["PRIV_"+privilege] #@UndefinedVariable
        return getCore().subscribe(addressType, address, subscription, privilege).toDict()
    
    def xmlrpc_unsubscribe(self, addressType, address):
        addressType = contacts.__dict__["AT_"+addressType] #@UndefinedVariable
        return getCore().unsubscribe(addressType, address)
