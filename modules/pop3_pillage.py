#! /usr/bin/python
import email.parser
import imaplib
import os
import poplib
import re
import ssl
from threading import Thread

from modules.pillager import Pillager

# -----------------------------------------------------------------------------
# POP3 subclass of Pillager Class
# -----------------------------------------------------------------------------
class POP3(Pillager):
    def __init__(self):
        Pillager.__init__(self)
        self.msg_list = None

    def connect(self, config):
        self.config = config
        try:
            self.srv = poplib.POP3(self.config["server"], self.config["serverport"])
        except:
            self.srv = None
            pass

    def disconnect(self):
        if (self.srv):
            self.srv.quit()

    def validate(self, user, password):
        if (not self.srv):
            return

        self.user = user
        self.password = password
        try:
            self.srv.user(self.user)
            self.srv.pass_(self.password)
        except poplib.error_proto as e:
            return False
        return True

    def searchMessageBodies(self, term=None):
        if (not self.srv):
            return []

        if (not term):
            return []

        self.getMessages()

        matched = []
        i = 1
        for (server_msg, body, octets) in self.msg_list:
            body = '\n'.join(body)
            for search_term in term:
                if re.search(search_term, body, re.IGNORECASE):
                    print "MATCHED ON [%s]" % (search_term)
                    if not i in matched:
                        matched.append(i)
            i = i + 1
        return matched

    def searchMessageSubjects(self, term=None):
        if (not self.srv):
            return []

        if (not term):
            return []

        self.getMessages()

        matched = []
        i = 1
        for (server_msg, body, octets) in self.msg_list:
            msg = email.message_from_string('\n'.join(body))
            for search_term in term:
                if re.search(search_term, msg['subject'], re.IGNORECASE):
                    print "MATCHED ON [%s]" % (search_term)
                    if not i in matched:
                        matched.append(i)
            i = i + 1
        return matched

    def searchMessageAttachments(self, term=None):
        if (not self.srv):
            return []

        if (not term):
            return []

        self.getMessages()

        matched = []
        i = 1
        for (server_msg, body, octets) in self.msg_list:
            msg = email.message_from_string('\n'.join(body))

            # save attach
            for part in msg.walk():
                if part.get_content_maintype() == 'multipart':
                    continue

                if part.get('Content-Disposition') is None:
                    continue

                filename = part.get_filename()

                if not (filename):
                    continue

                for search_term in term:
                    if re.search(search_term, filename, re.IGNORECASE):
                        print "MATCHED ON [%s]" % (search_term)
                        if not i in matched:
                            matched.append(i)
            i = i + 1
        return matched

    def downloadMessage(self, messageid=None):
        if (not self.srv):
            return

        if messageid:
            (server_msg, body, octets) = self.srv.retr(messageid)

            filename = self.user + "_" + str(messageid)
            file_path = os.path.join(self.config["outdir"], filename)

            print "Downloading message id [%s] to [%s]" % (messageid, file_path)
            # Check if its already there
            if not os.path.isfile(file_path):
                # finally write the stuff
                fp = open(file_path, 'wb')
                fp.write('\n'.join(body))
                fp.close()
        return None

    def downloadAttachment(self, messageid=None):
        if (not self.srv):
            return

        if (not messageid):
            return

        (server_msg, body, octets) = self.srv.retr(messageid)

        msg = email.message_from_string('\n'.join(body))

        # save attach
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue

            if part.get('Content-Disposition') is None:
                continue

            filename = part.get_filename()

            if not (filename):
                continue

            file_path = os.path.join(self.config["outdir"], filename)
            print "Downloading attachment [%s] to [%s]" % (messageid, file_path)

            # Check if its already there
            if not os.path.isfile(file_path):
                # finally write the stuff
                fp = open(file_path, 'wb')
                fp.write(part.get_payload(decode=True))
                fp.close()
        return None

    def scrapeContacts(self):
        if (not self.srv):
            return

        self.getMessages()

        contacts = []
        for (server_msg, body, octets) in self.msg_list:
            mail = email.message_from_string('\n'.join(body))
            for part in mail.walk():
                fromaddr = part['from']
                if (fromaddr):
                    sender = part['from'].split()[-1]
                    address = re.sub(r'[<>]', '', sender)
                    # Ignore any occurences of own email address and add to list
                    if not re.search(r'' + re.escape(self.user), address) and not address in contacts:
                        contacts.append(address)
                        print "IDENTIFED new contact [%s]" % (address)

        return contacts

    def getXsubjects(self, num=10):
        if (not self.srv):
            return

        self.getMessages()

        for (server_msg, body, octets) in self.msg_list:
            msg2 = email.message_from_string('\n'.join(body))
            print "[%s] -> [%s]" % (msg2['from'], msg2['subject'])

    def getMessages(self):
        if (not self.srv):
            return

        if (not self.msg_list):
            (numMsgs, totalSize) = self.srv.stat()
            self.msg_list = []
            for i in range(numMsgs):
                self.msg_list.append(self.srv.retr(i + 1))
