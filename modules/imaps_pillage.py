#! /usr/bin/python
import email.parser
import imaplib
import os
import poplib
import re
import ssl
from threading import Thread

from modules.pillager import Pillager
from modules.imap_pillage import IMAP

# -----------------------------------------------------------------------------
# IMAPS subclass of IMAP Class
# -----------------------------------------------------------------------------
class IMAPS(IMAP):
    def __init__(self):
        IMAP.__init__(self)

    def connect(self, config):
        self.config = config
        try:
            self.srv = imaplib.IMAP4_SSL(self.config["server"], self.config["serverport"])
        except:
            self.srv = None
            pass
