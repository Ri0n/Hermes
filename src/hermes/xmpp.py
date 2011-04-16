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
        self.spamReceivers = {}

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
            answer = """Тебя приветствует Великий и Ужасный ГЕРМЕС!!!
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
        elif text == "wantspam":
            self.startSendingSpam(message["from"])
            return
        elif text == "stopspam":
            self.stopSendingSpam(message["from"])
            return
        elif text[:2].strip(" ") == "S": # subscription
            new = text[2:].strip(" \n")
            if new:
                c = getCore().contacts.subscribe(AT_XMPP, j.userhost(), new)
                answer = "Великий Гермес запомнил вас как: " + str(c)
            else:
                c = getCore().contacts.getByAddress(AT_XMPP, j.userhost())
                answer = "Великий Гермес узнал вас как: " + str(c) if c else \
                    "Великий Гермес долго перебирал древние свитки, но так и не смог найти вашу подписку"
                answer += """\n\nЧто бы изменить свою подписку, попробуйте написать что-нибудь после буквы S
через пробел ;-) Учтите, что по-умолчанию нет никакой подписки.

Примеры:
1) S * - подписаться на всё
2) S @pamm[*],@billing[*] - подписатья на всё только для ПАММа и биллинга
3) S error,@pamm[warning] - подписаться на тег error, а для ПАММа ещё и на warning
4) S *,^notice - подписаться на всё кроме тега notice

На данный момент доступны следующие сервера:
"""
                for k, v in getCore().servicesDict().iteritems():
                    answer += "%s - %s\n" % (k, v)
        else:
            if datetime.datetime.today() - self.lastSendTime < datetime.timedelta(seconds=5):
                print "RATE LIMIT exceeded: ", message.toXml()
                return # don't send too often
            answer = "Хм, я не знаю что такое \"%s\". " \
                     "я вообще в принципе тупой.." % text
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
        
    def startSendingSpam(self, jid):
        def send10(jid):
            for i in range(1, 10):
                self.sendMessage([jid], "this is spam" + """
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
        """)
        
        self.spamReceivers[jid] = scheduler.job(send10, jid).repeated(1)
        self.spamReceivers[jid].start()

    def stopSendingSpam(self, jid):
        if jid in self.spamReceivers:
            self.spamReceivers[jid].cancel()
            del self.spamReceivers[jid]
        

