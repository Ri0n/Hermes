from rcore import config, Core
from twisted.python import log

AT_XMPP = 1
AT_EMAIL = 2

PRIV_GUEST = 0
PRIV_USER = 1
PRIV_ADMIN = 2


def regTextConstants(cs):
    d = dict()
    for k in cs:
        d[globals()[k]] = k
    return d

types = regTextConstants(["AT_XMPP","AT_EMAIL"])
privileges = regTextConstants(["PRIV_GUEST","PRIV_USER","PRIV_ADMIN"])

htypes = {AT_XMPP: "XMPP", AT_EMAIL: "E-Mail"}

def typeHStr(type):
    return htypes[type]

class Subscription(object):
    @classmethod
    def fromString(cls, data):
        s = cls()
        s.parse(data)
        return s
    
    def __str__(self):
        return ",".join([str(v) for v in self.services.values()]).strip(",")
    
    def parse(self, data):
        self.services = Core.instance().tagParser.servicesFromString(data)
        
    def match(self, sender, tags):
        r = None
        if sender in self.services:
            r = self.services[sender].match(tags)
        if r == None:
            r = self.services["__default__"].match(tags)
            assert r != None, "default service must be initialized with disableAll or enableAll"
        return r

class Contact(object):
    def __init__(self):
        self.type = None
        self.address = None
        self.privilege = None
        self.subscription = None
            
    @classmethod
    def fromDict(cls, d):
        c = cls()
        c.type = d["type"]
        c.address = d["address"]
        c.privilege = d["privilege"] if "privilege" in d else PRIV_USER;
        c.subscription = Subscription.fromString(d["subscription"] if "subscription" in d.keys() else '^*')
        #c.id = d.get("id", None)
        return c
            
    def __str__(self):
        return typeHStr(self.type) + ": " + self.address + " tags: " + str(self.subscription)
    
    def matchTags(self, sender, tags):
        return self.subscription.match(sender, tags)
    
    def matchAddress(self, type, address):
        return self.type == type and self.address == address
    
    def updateSubscription(self, subscriptionString):
        self.subscription.parse(subscriptionString)
        print ("Subscription updated: " + str(self))
        self.save()
        
    def save(self):
        c = Core.instance().db.cursor()
#        if self.id:
#            c.execute("UPDATE OR REPLACE contacts(type, address, privilege, subscription) "\
#                  "VALUES(?, ?, ?, ?)", (self.type, self.address, self.privilege, self.subscription))
#        else:
        c.execute("REPLACE INTO contacts(type, address, privilege, subscription) "\
                  "VALUES(?, ?, ?, ?)", (self.type, self.address, self.privilege, str(self.subscription)))
        c.close()
        
    def delete(self):
        c = Core.instance().db.cursor()
        c.execute("DELETE FROM contacts WHERE type=? AND address=?", (self.type, self.address))
    
    def toDict(self):
        return dict(
            type = types[self.type],
            address = self.address,
            privilege = privileges[self.privilege],
            subscription = str(self.subscription)
        )

class ContactsManager(object):

    def __init__(self):
        self.contacts = []
        cur = Core.instance().db.cursor()
        cur.execute("SELECT * FROM contacts")
        for row in cur:
            c = Contact.fromDict(row)
            print ("Loaded contact:", str(c))
            self.contacts.append(c)
            
            
    def getAdmins(self):
        ret = []
        for c in self.contacts:
            if c.privilege == PRIV_ADMIN:
                ret.append(c)
        return ret
    
    def getByAddress(self, addressType, address):
        for c in self.contacts:
            if c.matchAddress(addressType, address):
                return c
        return None

    def getSubscribers(self, sender, tags):
        tags = set(tags)
        return [c for c in self.contacts if c.matchTags(sender, tags)]
    
    def subscribe(self, addressType, address, subsciptionString, privilege = PRIV_USER):
        c = self.getByAddress(addressType, address)
        if c:
            c.updateSubscription(subsciptionString)
            return c
        c = Contact.fromDict(dict(
            type      = addressType,
            address   = address,
            privilege = privilege,
            subscription = subsciptionString
        ))
        c.save()
        print ("A new contact added:" + str(c))
        self.contacts.append(c)
        return c
    
    def unsubscribe(self, addressType, address):
        c = self.getByAddress(addressType, address)
        if c:
            c.delete()
            del self.contacts[self.contacts.index(c)]
            print ("unsubscribed:" + str(c))
            return True
        return False
