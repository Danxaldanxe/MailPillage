#! /usr/bin/python
import email.parser
import imaplib
import os
import poplib
import re
import ssl
from threading import Thread

from modules.pillager import Pillager
from modules.pop3_pillage import POP3

# -----------------------------------------------------------------------------
# POP3S subclass of POP3 Class
# -----------------------------------------------------------------------------
class POP3S(POP3):
    def __init__(self):
        POP3.__init__(self)

    def connect(self, config):
        self.config = config
        try:
            self.srv = poplib.POP3_SSL(self.config["server"], self.config["serverport"])
        except:
            self.srv = None
            pass
