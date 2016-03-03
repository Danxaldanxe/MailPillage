#!/usr/bin/python

import base64
import httplib
import os
import re
from lxml import etree

from modules.pillager import Pillager

# -----------------------------------------------------------------------------
# IMAP subclass of Pillager Class
# -----------------------------------------------------------------------------
class EWS(Pillager):
    def __init__(self):
        Pillager.__init__(self)
        self.uids = None
        self.url = ""
        self.user = ""
        self.password = ""

    def connect(self, config):
        self.config = config
        self.url = "http://" + self.config["server"] + "/ews/Exchange.asmx"
        return

    def disconnect(self):
        return

    def buildConn(self, request):
        # Build authentication string, remove newline for using it in a http header
        auth = base64.encodestring("%s:%s" % (self.user, self.password)).replace('\n', '')
        conn = httplib.HTTPSConnection(self.config["server"])
        conn.request("POST", self.url, body=request, headers={
            "Host": self.config["server"],
            "Content-Type": "text/xml; charset=UTF-8",
            "Content-Length": len(request),
            "Authorization": "Basic %s" % auth
        })
        # Read the webservice response
        resp = conn.getresponse()
        status = resp.status
        data = resp.read()
        conn.close()
        return (status, data)

    def validate(self, user, password):
        self.user = user
        self.password = password
        request = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
  <soap:Body>
    <FindItem xmlns="http://schemas.microsoft.com/exchange/services/2006/messages"
               xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types"
              Traversal="Shallow">
      <ItemShape>
        <t:BaseShape>Default</t:BaseShape>
      </ItemShape>
      <ParentFolderIds>
        <t:DistinguishedFolderId Id="inbox"/>
      </ParentFolderIds>
    </FindItem>
  </soap:Body>
</soap:Envelope>""".format()

        (status, data) = self.buildConn(request)
        if (int(status) == 401):
            return False
        return True

    def pillage(self):
        self.searchMessages(self.config["searchterms"])

    def searchMessages(self, term):
        request = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
      <soap:Body>
        <FindItem xmlns="http://schemas.microsoft.com/exchange/services/2006/messages"
                   xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types"
                  Traversal="Shallow">
          <ItemShape>
            <t:BaseShape>Default</t:BaseShape>
          </ItemShape>
          <ParentFolderIds>
            <t:DistinguishedFolderId Id="inbox"/>
          </ParentFolderIds>
        </FindItem>
      </soap:Body>
    </soap:Envelope>""".format()

        # authenticate, issue request, get response
        (status, data) = self.buildConn(request)

        # Parse the result xml
        root = etree.fromstring(data)

        xpathStr = "/s:Envelope/s:Body/m:FindItemResponse/m:ResponseMessages/m:FindItemResponseMessage/m:RootFolder/t" \
                   ":Items/t:Message"
        namespaces = {
            's': 'http://schemas.xmlsoap.org/soap/envelope/',
            't': 'http://schemas.microsoft.com/exchange/services/2006/types',
            'm': 'http://schemas.microsoft.com/exchange/services/2006/messages',
        }

        contacts = []
        # Print Mail properties
        elements = root.xpath(xpathStr, namespaces=namespaces)
        for element in elements:
            try:
                subject = element.find('{http://schemas.microsoft.com/exchange/services/2006/types}Subject').text
                fromname = element.find(
                    '{http://schemas.microsoft.com/exchange/services/2006/types}From/{'
                    'http://schemas.microsoft.com/exchange/services/2006/types}Mailbox/{'
                    'http://schemas.microsoft.com/exchange/services/2006/types}Name').text
                fromemail = element.find(
                    '{http://schemas.microsoft.com/exchange/services/2006/types}From/{'
                    'http://schemas.microsoft.com/exchange/services/2006/types}Mailbox/{'
                    'http://schemas.microsoft.com/exchange/services/2006/types}EmailAddress').text
                itemid = element.find('{http://schemas.microsoft.com/exchange/services/2006/types}ItemId').attrib['Id']
                changekey = element.find('{http://schemas.microsoft.com/exchange/services/2006/types}ItemId').attrib[
                    'ChangeKey']

                contacts.append(fromname.encode('ascii', 'ignore') + " (" + fromemail.encode('ascii', 'ignore') + ")")

                for search_term in term:
                    if re.search(search_term, subject, re.IGNORECASE):
                        print "-------------------------------------------"
                        print "MATCHED ON [%s]" % (search_term)
                        print "* Subject : " + subject.encode('ascii', 'ignore')
                        print "* From : " + fromname.encode('ascii', 'ignore') + " (" + fromemail.encode('ascii',
                                                                                                         'ignore') + ")"
                        if self.config["downloademails"]:
                            body = self.getBody(itemid, changekey)
                            #self.writeMessage(fromname.encode('ascii', 'ignore').replace(" ", "_") + (subject.encode('ascii', 'ignore').replace(" ", "_")), body)
                            tempname = fromname.encode('ascii', 'ignore').replace(" ", "_") + (subject.encode('ascii', 'ignore').replace(" ", "_"))
                            filename = "".join(c for c in tempname if c.isalnum()).rstrip()
                            self.writeMessage(filename, body)
            except:
                pass

        if self.config["buildcontactlist"]:
            # print out any collected contacts
            for contact in sorted(set(contacts)):
                print contact

    def writeMessage(self, messageid, text):
        filename = self.user + "_" + messageid
        filename = "".join(c for c in filename if c.isalnum()).rstrip()
        file_path = os.path.join(self.config["outdir"], filename)

        print "Downloading message id [%s] to [%s]" % (messageid, file_path)
        # Check if its already there
        if not os.path.isfile(file_path):
            # finally write the stuff
            fp = open(file_path, 'wb')
            fp.write(email_body)
            fp.close()

    def getBody(self, itemid, changekey):
        request = """<?xml version="1.0" encoding="utf-8"?>
    <soap:Envelope
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xmlns:xsd="http://www.w3.org/2001/XMLSchema"
      xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
      xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
      <soap:Body>
        <GetItem
          xmlns="http://schemas.microsoft.com/exchange/services/2006/messages"
          xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types">
          <ItemShape>
            <t:BaseShape>Default</t:BaseShape>
            <t:IncludeMimeContent>true</t:IncludeMimeContent>
          </ItemShape>
          <ItemIds>
            <t:ItemId Id="{0}" ChangeKey="{1}" />
          </ItemIds>
        </GetItem>
      </soap:Body>
    </soap:Envelope>""".format(itemid, changekey)

        # authenticate, issue request, get response
        (status, data) = self.buildConn(request)

        # Parse the result xml
        root = etree.fromstring(data)

        # start xpath
        xpathStr = "/s:Envelope/s:Body/m:GetItemResponse/m:ResponseMessages/m:GetItemResponseMessage/m:Items/t:Message"

        namespaces = {
            's': 'http://schemas.xmlsoap.org/soap/envelope/',
            't': 'http://schemas.microsoft.com/exchange/services/2006/types',
            'm': 'http://schemas.microsoft.com/exchange/services/2006/messages',
        }

        # Print Mail Body
        elements = root.xpath(xpathStr, namespaces=namespaces)
        for element in elements:
            body = element.find('{http://schemas.microsoft.com/exchange/services/2006/types}Body').text
            return body.encode('ascii', 'ignore')
        return ""
