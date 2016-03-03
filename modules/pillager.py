#! /usr/bin/python
import email.parser
import imaplib
import os
import poplib
import re
import ssl
from threading import Thread

# -----------------------------------------------------------------------------
# Primary Pillager Class that all others are sub classes of
# This really does nothing and is just a place holder
# -----------------------------------------------------------------------------
class Pillager():
    def __init__(self):
        self.config = None
        self.srv = None
        self.servertype = None

    def getType(self):
        return self.servertype

    def connect(self, config):
        self.config = config
        self.srv = None

    def disconnect(self):
        return

    def validate(self, user, password):
        return False

    def pillage(self):
        if self.config["downloademails"]:
            print self.config["searchterms"]
            matched_messages = []
            print "---------------Search Message Bodies [credential, account, password, login]"
            matched_messages.extend(self.searchMessageBodies(term=self.config["searchterms"]))
            print "---------------Search Message Subjects [credential, account, password, login]"
            matched_messages.extend(self.searchMessageSubjects(term=self.config["searchterms"]))
            print "---------------Download Messages"
            for uid in set(matched_messages):
                self.downloadMessage(uid)
        if self.config["downloadattachments"]:
            matched_attachments = []
            print "---------------Search Message Attachments [credential, account, password, login]"
            matched_attachments.extend(self.searchMessageAttachments(term=self.config["searchterms"]))
            print "---------------Download Attachments"
            for uid in set(matched_attachments):
                self.downloadAttachment(uid)
        if self.config["buildcontactlist"]:
            print "---------------Scrape Contacts"
            print self.scrapeContacts()

        return

    def searchMessageBodies(self, term=None):
        return []
    def searchMessageSubjects(self, term=None):
        return []
    def searchMessageAttachments(self, term=None):
        return []
    def downloadAttachment(self, uid):
        return
    def scrapeContacts(self):
        return
