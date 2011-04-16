# To change this template, choose Tools | Templates
# and open the template in the editor.

import sqlite3
import os

from twisted.python import log
from xml.sax.saxutils import escape


from rcore import config, Core
from hermes import demon, xmpp
from hermes.contacts import ContactsManager, AT_XMPP
from hermes.tag_parser import TagParser

class HermesCore(Core):
    def run(self):
        log.msg("Init hermes logic unit instance")
        self.tagParser = TagParser()
        
        # preparing database
        self.db = sqlite3.connect(os.path.join(config().spool.path,config().spool.db))
        self.db.isolation_level = None
        self.db.row_factory = sqlite3.Row

        c = self.db.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS contacts
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 type INTEGER,
                 address TEXT,
                 privilege INTEGER,
                 subscription TEXT)''')
        c.execute('''CREATE UNIQUE INDEX IF NOT EXISTS uniq_contact_address
                ON contacts(type, address)''')

        self.contacts = ContactsManager()
        self.xmpp = xmpp.XmppMessenger()
        
        demon.init()
        super(HermesCore, self).run()

    def auth(self, user, password):
        logins = config().logins.login
        authorized = filter(lambda l:l.user == user and l.password == password, logins)
        if len(authorized):
            self.senderName = " or ".join([i.name for i in authorized])
            self.senderLogin = user
            return True
        return False
    
    def servicesDict(self):
        ret = {}
        logins = config().logins.login
        for l in logins:
            ret[l.user] = l.name
        return ret


    def notify(self, message, tags):
        if isinstance(message, list):
            message, messageHtml = message
        else:
            messageHtml = escape(message).replace("\n", "<br/>")
            
        tagsText = " ".join(["*"+tag for tag in tags])
        
        text = "Sender: " + self.senderName + "\n" + tagsText + "\n\n" + message
        
        html = "<div style='font-weight:bold; color:#000008'>Sender: " + escape(self.senderName) + "</div>"
        html += "<div style='color:#808080'>" + tagsText + "</div>"
        html += "<div style='margin-top:1em'>" + messageHtml + "</div>"
        
        self.xmpp.sendMessage([c.address for c in self.contacts.getSubscribers(self.senderLogin, tags) if c.type == AT_XMPP],
                              text, html)
        
    def notifyAll(self, message):
        self.directNotify(message, self.contacts.contacts)
        
    def directNotify(self, message, recipients):
        if isinstance(message, list):
            message, messageHtml = message
        else:
            messageHtml = escape(message).replace("\n", "<br/>")
            
        text = "Sender: " + self.senderName + "\n\n" + message
        
        html = "<div style='font-weight:bold; color:#000008'>Sender: " + escape(self.senderName) + "</div>"
        html += "<div style='margin-top:1em'>" + messageHtml + "</div>"
        
        self.xmpp.sendMessage([c.address for c in recipients if c.type == AT_XMPP], 
                              text, html)
        
    def getContacts(self):
        return self.contacts.contacts
    
    def subscribe(self, addressType, address, subscription, privelege):
        return self.contacts.subscribe(addressType, address, subscription, privelege)
    
    def unsubscribe(self, addressType, address):
        return self.contacts.unsubscribe(addressType, address)
    
    