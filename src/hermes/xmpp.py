import datetime
# -*- coding: utf-8 -*-

import re
import htmlentitydefs

from twisted.web.client import getPage
from twisted.internet import reactor
from twisted.names.srvconnect import SRVConnector
from twisted.words.xish import domish, xpath
from twisted.words.protocols.jabber import xmlstream, client, jid
from twisted.python import log

import messenger
from rcore import config, scheduler
from hermes.contacts import Contact, AT_XMPP
from rcore.globals import getCore

MessageWithBody = xpath.internQuery("/message/body")
MessageWithError = xpath.internQuery("/message/error")


##
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.

def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def parseXML(serialized):
    result = []
    def onStart(el):
        result.append(el)

    def onElement(el):
        result[0].addChild(el)

    parser = domish.elementStream()
    parser.DocumentStartEvent = onStart
    parser.ElementEvent = onElement
    parser.DocumentEndEvent = lambda: None
    parser.parse("<r>" + serialized + "</r>")
    return result[0].children
    


class XMPPClientConnector(SRVConnector):
    def __init__(self, reactor, domain, factory):
        SRVConnector.__init__(self, reactor, 'xmpp-client', domain, factory)


    def pickServer(self):
        host, port = SRVConnector.pickServer(self)

        if not self.servers and not self.orderedServers:
            # no SRV record, fall back..
            port = int(config().xmpp.port)

        return host, port


class XmppMessenger(messenger.Messenger):

    keepAlivePeriod = 120 #should be > 30

    def __init__(self):
        super(XmppMessenger, self).__init__()
        self.me = jid.JID(config().xmpp.me)
        self.xmlstream = False
        self.kaTimer = None
        self.kaResponseTimer = None
        self.lastSendTime = datetime.datetime.today() - datetime.timedelta(days=1)

        f = client.XMPPClientFactory(self.me, config().xmpp.password)
        f.addBootstrap(xmlstream.STREAM_CONNECTED_EVENT, self.connected)
        f.addBootstrap(xmlstream.STREAM_END_EVENT, self.disconnected)
        f.addBootstrap(xmlstream.STREAM_AUTHD_EVENT, self.authenticated)
        f.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.init_failed)
        self.connector = XMPPClientConnector(reactor, self.me.host, f)
        self.connect()

    def connect(self):
        self.connector.connect()

    def reconnect(self):
        print "call reconnect"
        self.resetKeepAlive()
        if self.xmlstream:
            self.xmlstream.sendFooter()
            self.connector.disconnect()
        self.connect()

    def keepAlive(self):
        if not self.kaResponseTimer and self.xmlstream:
            iq = client.IQ(self.xmlstream, "get")
            iq["to"] = self.me.host
            iq.addElement('ping', "urn:xmpp:ping")
            iq.addCallback(self.reinitKeepAlive)
            self.kaResponseTimer = reactor.callLater(30, self.reconnect)
            iq.send()

    def resetKeepAlive(self):
        if self.kaResponseTimer and self.kaResponseTimer.active():
            self.kaResponseTimer.cancel()
        if self.kaTimer and self.kaTimer.active():
            self.kaTimer.cancel()
        self.kaResponseTimer = None
        self.kaTimer = None

    def planKeepAlive(self):
        self.kaTimer = reactor.callLater(self.keepAlivePeriod, self.keepAlive)

    def reinitKeepAlive(self, *args):
        self.resetKeepAlive()
        self.planKeepAlive()

    def rawDataIn(self, buf):
        self.reinitKeepAlive()
        #print "RECV: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')


    def rawDataOut(self, buf):
        self.reinitKeepAlive()
        #print "SEND: %s" % unicode(buf, 'utf-8').encode('ascii', 'replace')


    def connected(self, xs):
        print 'Connected.'

        self.xmlstream = xs
        self.xmlstream.addObserver(MessageWithBody, self.processMessageBody)

        # Log all traffic
        xs.rawDataInFn = self.rawDataIn
        xs.rawDataOutFn = self.rawDataOut


    def disconnected(self, xs):
        print 'Disconnected.'
        self.resetKeepAlive()
        self.xmlstream = False
        #reactor.stop()


    def authenticated(self, xs):
        print "Authenticated."

        presence = domish.Element((None, 'presence'))
        xs.send(presence)

        #reactor.callLater(5, xs.sendFooter)
        self.planKeepAlive()


    def init_failed(self, failure):
        print "Initialization failed."
        print failure

        self.xmlstream.sendFooter()

    def processMessageBody(self, message):
        if MessageWithError.matches(message):
            return # silently ignore error responces
        j = jid.JID(message["from"])
        if j.host != self.me.host:
            return #ignore other domains
        text = str(message.body)
        if text.lower() == "help":
            answer = """The Great HERMES welcomes you!!!
Хотя можешь называть меня просто "О, великий", я не обижусь.
Итак, смертный, ты посмел попросить у меня помощи и на твое везение я сегодня
крайне добр и великодушен, посему спрашивай чего ты хочешь:

ibash - читать ibash
S - подписка
"""
        elif text.lower() in ["привет", "hi", "хай"]:
            answer = "и вам здоровья, боярин!"
        elif text == ".":
            answer = "..-.---....-..--..."
        elif text == "ibash":
            self.sendIBashTo(message["from"])
            return
        elif text[:2].strip(" ") == "S": # subscription
            new = text[2:].strip(" \n")
            if new:
                c = getCore().contacts.subscribe(AT_XMPP, j.userhost(), new)
                answer = "The Greate Hermes remembered you: " + str(c)
            else:
                c = getCore().contacts.getByAddress(AT_XMPP, j.userhost())
                answer = "The Great Hermes knows you as: " + str(c) if c else \
                    "The Great Hermes really tried to find you in ancient scrolls but unsuccessfully"
                answer += """\n\nTo change your subscribtion try to write something after letter S
after space ;-) Keep in mind there is no any subscription by default.

Examples:
1) S * - subscribe to everything
2) S @serv1[*],@serv2[*] - subscribe to everything for serv1 and serv2
3) S error,@serv1[warning] - subscribe to tag "error" but for serv1 "warning" as well
4) S *,^notice - subscrive to everything except "notice" tag

Next services are available:
"""
                for k, v in getCore().servicesDict().iteritems():
                    answer += "%s - %s\n" % (k, v)
        else:
            if datetime.datetime.today() - self.lastSendTime < datetime.timedelta(seconds=5):
                print "RATE LIMIT exceeded: ", message.toXml()
                return # don't send too often
            answer = "Hm I don't know what is \"%s\". " \
                     "I'm just stupid bot.." % text
        self.sendMessage([message["from"]], answer)

    def sendIBashTo(self, jid):
        def toText(result):
            m = re.search('<div class="quotbody">(.*)</div>', result.decode("windows-1251"))
            if m:
                try:
                    msg = re.sub("(<br */>)", "\n", m.group(1))
                    msg = unescape(msg)
                except Exception, e:
                    msg = ":-("
                    log.err()
                print repr(msg)
                self.sendMessage([jid], msg)
            else:
                self.sendMessage([jid], "ibash сломалсо :-(")
        d = getPage("http://ibash.org.ru/random.php")
        d.addCallback(toText)

    def sendMessage(self, addresses, text, html = ""):
        if not self.xmlstream:
            print "XML Stream is not ready yet! Can't send: ", text
            return
        message = domish.Element((None, 'message'))
        message["type"] = "chat"
        message.addElement('body', content=text)
        if html:
            try:
                elements = parseXML(html)
                he = message.addElement(('http://jabber.org/protocol/xhtml-im', 'html'))
                body = he.addElement(('http://www.w3.org/1999/xhtml', 'body'))
                for e in elements:
                    body.addChild(e)
            except Exception, e:
                print "Failed to add xhtml content:", str(e)
        
        for j in addresses:
            log.msg("sending message to " + j)
            message["to"] = j
            self.xmlstream.send(message)
        self.lastSendTime = datetime.datetime.today()

