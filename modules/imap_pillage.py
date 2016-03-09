#! /usr/bin/python
import email.parser
import imaplib
import os
import poplib
import re
import ssl
from threading import Thread

from modules.pillager import Pillager
from core.utils import Utils

# -----------------------------------------------------------------------------
# IMAP subclass of Pillager Class
# -----------------------------------------------------------------------------
class IMAP(Pillager):
    def __init__(self):
        Pillager.__init__(self)
        self.uids = None

    def connect(self, config):
        self.config = config
        try:
            self.srv = imaplib.IMAP4(self.config["server"])
        except:
            self.srv = None
            pass

    def disconnect(self):
        if (self.srv):
#            self.srv.close()
            self.srv.logout()

    def validate(self, user, password):
        if (not self.srv):
            return

        self.user = user
        self.password = password
        try:
            self.srv.login(user, password)
        except ssl.SSLError as e:
            return False
        except imaplib.IMAP4.error as e:
            return False
        return True

    def searchMessageBodies(self, term=None):
        if (not self.srv):
            return []

        if (not term):
            return []

        matched = []
        self.srv.select(readonly=True)
        search_term = self.buildSearchTerm("Body", term)
        typ, data = self.srv.search(None, search_term)
        for uid in data[0].split():
            print "MATCHED ON [%s]" % (uid)

            if not uid in matched:
                matched.append(uid)
        return matched

    def searchMessageSubjects(self, term=None):
        if (not self.srv):
            return []

        if (not term):
            return []

        matched = []
        self.srv.select(readonly=True)
        search_term = self.buildSearchTerm("Subject", term)
        typ, data = self.srv.search(None, search_term)
        for uid in data[0].split():
            header = self.srv.fetch(uid, '(BODY[HEADER])')
            if (header):
                header_data = header[1][0][1]
                parser = email.parser.HeaderParser()
                msg = parser.parsestr(header_data)
                print "#%s [%s] -> [%s]" % (uid, msg['from'], msg['subject'])

                if not uid in matched:
                    matched.append(uid)
        return matched

    def searchMessageAttachments(self, term=None):
        if (not self.srv):
            return []

        self.getUIDs()

        if (not self.uids):
            return []

        matched = []
        for uid in self.uids:
            resp, data = self.srv.fetch(uid,
                                        "(RFC822)")  # fetching the mail, "`(RFC822)`" means "get the whole stuff",
            # but you can ask for headers only, etc
            email_body = data[0][1]  # getting the mail content
            mail = email.message_from_string(email_body)  # parsing the mail content to get a mail object

            # Check if any attachments at all
            if mail.get_content_maintype() != 'multipart':
                continue

            print "[" + mail["From"] + "] :" + mail["Subject"]

            # we use walk to create a generator so we can iterate on the parts and forget about the recursive headach
            for part in mail.walk():
                # multipart are just containers, so we skip them
                if part.get_content_maintype() == 'multipart':
                    continue

                # is this part an attachment ?
                if part.get('Content-Disposition') is None:
                    continue

                filename = part.get_filename()
                print "Found attachment [%s]" % (filename)

                valid = False
                if (term):
                    for search_term in term:
                        if re.match(search_term, filename, re.IGNORECASE):
                            print "MATCHED ON [%s]" % (search_term)
                            valid = True
                else:
                    valid = True

                if valid:
                    print "Filename [%s] MATCHED search terms for uid [%s]" % (filename, uid)
                    if not uid in matched:
                        matched.append(uid)
        return matched

    def downloadMessage(self, messageid=None):
        if (not self.srv):
            return

        if messageid:
            resp, data = self.srv.fetch(messageid,
                                        "(RFC822)")  # fetching the mail, "`(RFC822)`" means "get the whole stuff",
            # but you can ask for headers only, etc
            email_body = data[0][1]  # getting the mail content

            filename = self.user + "_" + messageid
            file_path = os.path.join(self.config["outdir"], filename)

            print "Downloading message id [%s] to [%s]" % (messageid, file_path)
            Utils.writeFile(email_body, file_path)
        return None

    def downloadAttachment(self, messageid=None):
        if (not self.srv):
            return

        if messageid:
            resp, data = self.srv.fetch(messageid,
                                        "(RFC822)")  # fetching the mail, "`(RFC822)`" means "get the whole stuff",
            # but you can ask for headers only, etc
            email_body = data[0][1]  # getting the mail content
            mail = email.message_from_string(email_body)  # parsing the mail content to get a mail object

            # Check if any attachments at all
            if mail.get_content_maintype() != 'multipart':
                return

            # we use walk to create a generator so we can iterate on the parts and forget about the recursive headach
            for part in mail.walk():
                # multipart are just containers, so we skip them
                if part.get_content_maintype() == 'multipart':
                    continue

                # is this part an attachment ?
                if part.get('Content-Disposition') is None:
                    continue

                filename = part.get_filename()

                if (not filename):
                    continue

                file_path = os.path.join(self.config["outdir"], filename)
                print "Downloading attachment [%s] to [%s]" % (messageid, file_path)
                Utils.writeFile(part.get_payload(decode=True), file_path, "wb")
        return

    def scrapeContacts(self):
        if (not self.srv):
            return

        self.getUIDs()

        if (not self.uids):
            return None

        contacts = []
        for uid in self.uids:
            resp, data = self.srv.fetch(uid, "(RFC822)")
            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_string(response_part[1])
                    fromaddr = msg['from']
                    if (fromaddr):
                        sender = msg['from'].split()[-1]
                        address = re.sub(r'[<>]', '', sender)
                        # Ignore any occurences of own email address and add to list
                        if not re.search(r'' + re.escape(self.user), address) and not address in contacts:
                            contacts.append(address)
                            print "IDENTIFED new contact [%s]" % (address)

        return contacts

    def getXsubjects(self, num=10):
        if (not self.srv):
            return

        numMessages = self.srv.select(readonly=True)[1][0]
        typ, data = self.getMessagesReverseOrder()
        maxNum = num
        if (numMessages < num):
            maxNum = numMessages

        i = 1
        for num in data[0].split():
            header = self.srv.fetch(num, '(BODY[HEADER])')
            if (header):
                header_data = header[1][0][1]
                parser = email.parser.HeaderParser()
                msg = parser.parsestr(header_data)
                print "#%i [%s] -> [%s]" % (i, msg['from'], msg['subject'])
            i = i + 1
            if (i > maxNum):
                return
        return None

    def getUIDs(self):
        if (not self.srv):
            return

        if (not self.uids):
            # get uids of all messages
            self.srv.select(readonly=True)
            result, data = self.srv.search(None, 'ALL')
            self.uids = data[0].split()

    def getMessagesReverseOrder(self, search_term='ALL'):
        if (not self.srv):
            return

        self.srv.select(readonly=True)
        sort_criteria = 'REVERSE DATE'
        return self.srv.sort(sort_criteria, 'UTF-8', search_term)

    def buildSearchTerm(self, part, terms):
        if (not self.srv):
            return

        if (not part) or (not terms):
            return

        term_string = ""
        i = 0
        for term in terms:
            temp = '(%s "%s")' % (part, term)
            if (i > 0):
                term_string = '(OR %s %s)' % (term_string, temp)
            else:
                term_string = temp
            i = i + 1
        return term_string
