import ConfigParser
import fcntl
import os
import random
import socket
import string
import struct
import subprocess
import sys
import time


class Utils():
    @staticmethod
    def port_open(ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((ip,int(port)))
        if result == 0:
           return True
        else:
           return False

    @staticmethod
    def to_unicode_str(obj, encoding='utf-8'):
        # checks if obj is a string and converts if not
        if not isinstance(obj, basestring):
            obj = str(obj)
        obj = Utils.to_unicode(obj, encoding)
        return obj

    @staticmethod
    def to_unicode(obj, encoding='utf-8'):
        # checks if obj is a unicode string and converts if not
        if isinstance(obj, basestring):
            if not isinstance(obj, unicode):
                obj = unicode(obj, encoding)
        return obj

    @staticmethod
    def newLine():
        return os.linesep

    @staticmethod
    def isWriteable(filename):
        try:
            fp = open(filename, 'a')
            fp.close()
            return True
        except IOError:
            return False

    @staticmethod
    def isReadable(filename):
        if not filename:
            return False
        try:
            fp = open(filename, 'r')
            fp.close()
            return True
        except IOError:
            return False

    @staticmethod
    def isExecutable(filename):
        return Utils.fileExists(filename) and os.access(filename, os.X_OK)

    @staticmethod
    def fileExists(filename):
        return os.path.isfile(filename)

    @staticmethod
    def writeFile(text, filename, flag="a"):
        fullfilename = os.path.abspath(filename+"_"+Utils.getRandStr(10))
        if not os.path.exists(os.path.dirname(fullfilename)):
            os.makedirs(os.path.dirname(fullfilename))
        fp = open(fullfilename, flag)
        fp.write(text)
        fp.close()

    @staticmethod
    def validateExecutable(name):
        path = None
        # yes I know this is an obvious command injection...
        # but we trust the users correct?  ;)
        tmp = Utils.execWait("which " + name).strip()
        if (tmp) and (tmp != "") and Utils.isExecutable(tmp):
            path = tmp
        return path

    @staticmethod
    def getRandStr(length):
        return ''.join(random.choice(string.lowercase) for i in range(length))

    @staticmethod
    def loadConfig(filename):
        config = {}
        if Utils.isReadable(filename):
            parser = ConfigParser.SafeConfigParser()
            parser.read(filename)
            for section_name in parser.sections():
                for name, value in parser.items(section_name):
                    config[name] = value
        return config

    @staticmethod
    def uniqueList(old_list):
        new_list = []
        if old_list != []:
            for x in old_list:
                if x not in new_list:
                    new_list.append(x)
        return new_list

    @staticmethod
    def execWait(cmd, outfile=None, timeout=0):
        result = ""
        env = os.environ
        timeout_cmd = ""
        if timeout:
            timeout_cmd = "timeout " + str(timeout) + " "
        proc = subprocess.Popen(timeout_cmd + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        result = proc.communicate()[0]
        if outfile:
            if Utils.fileExists(outfile):
                print "FILE ALREADY EXISTS!!!!"
            else:
                tmp_result = "\033[0;33m(" + time.strftime(
                    "%Y.%m.%d-%H.%M.%S") + ") <pentest> #\033[0m " + cmd + Utils.newLine() + Utils.newLine() + result
                Utils.writeFile(tmp_result, outfile)
        return result

    @staticmethod
    def webScreenCap(url, outfile):
        cmd = 'phantomjs --ssl-protocol=any --ignore-ssl-errors=yes misc/capture.js "%s" "%s"' % (url, outfile)
        Utils.execWait(cmd)
        return

    @staticmethod
    def getInterfaceIP(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15]))[20:24])

    @staticmethod
    def getIP():
        ip = socket.gethostbyname(socket.gethostname())
        if ip.startswith("127."):
            interfaces = ["eth0", "eth1", "eth2", "wlan0", "wlan1", "wifi0", "ath0", "ath1", "ppp0", ]
            for ifname in interfaces:
                try:
                    ip = Utils.getInterfaceIP(ifname)
                    break
                except IOError:
                    pass
        return ip

    @staticmethod
    def getUnusedPort():
        port = 0
        # determine free port
        return port


class Colors(object):
    N = '\033[m'  # native
    R = '\033[31m'  # red
    G = '\033[32m'  # green
    O = '\033[33m'  # orange
    B = '\033[34m'  # blue


class ProgressBar():
    def __init__(self, end=100, width=10, title="", display=None):
        self.end = end
        self.width = width
        self.title = title
        self.display = display
        self.progress = float(0)
        self.bar_format = '[%(fill)s>%(blank)s] %(progress)s%% - %(title)s'
        self.rotate_format = '[Processing: %(mark)s] %(title)s'
        self.markers = '|/-\\'
        self.curmark = -1
        self.completed = False
        self.reset()

    def reset(self, end=None, width=None, title=""):
        self.progress = float(0)
        self.completed = False
        if (end):
            self.end = end
        if (width):
            self.width = width
        self.curmark = -1
        self.title = title

    def inc(self, num=1):
        if (not self.completed):
            self.progress += num

            cur_width = (self.progress / self.end) * self.width
            fill = int(cur_width) * "-"
            blank = (self.width - int(cur_width)) * " "
            percentage = int((self.progress / self.end) * 100)

            if (self.display):
                self.display.verbose(
                    self.bar_format % {'title': self.title, 'fill': fill, 'blank': blank, 'progress': percentage},
                    rewrite=True, end="", flush=True)
            else:
                sys.stdout.write('\r' + self.bar_format % {'title': self.title, 'fill': fill, 'blank': blank,
                                                           'progress': percentage})
                sys.stdout.flush()

            if (self.progress == self.end):
                self.done()
        return self.completed

    def done(self):
        self.completed = True

    def rotate(self):
        if (not self.completed):
            self.curmark = (self.curmark + 1) % len(self.markers)
            if (self.display):
                self.display.verbose(self.rotate_format % {'title': self.title, 'mark': self.markers[self.curmark]},
                                     rewrite=True, end="", flush=True)
            else:
                sys.stdout.write('\r' + self.rotate_format % {'title': self.title, 'mark': self.markers[self.curmark]})
                sys.stdout.flush()
        return self.completed


class Display():
    def __init__(self, verbose=False, debug=False, logpath=None):
        self.VERBOSE = verbose
        self.DEBUG = debug
        self.logpath = logpath
        self.ruler = '-'

    def setLogPath(self, logpath):
        self.logpath = logpath

    def enableVerbose(self):
        self.VERBOSE = True

    def enableDebug(self):
        self.DEBUG = True

    def log(self, s, filename="processlog.txt"):
        if (self.logpath is not None):
            fullfilename = self.logpath + filename
            if not os.path.exists(os.path.dirname(fullfilename)):
                os.makedirs(os.path.dirname(fullfilename))
            fp = open(fullfilename, "a")
            if (filename == "processlog.txt"):
                fp.write(time.strftime("%Y.%m.%d-%H.%M.%S") + " - " + s + "\n")
            else:
                fp.write(s)
            fp.close()

    def _display(self, line, end="\n", flush=True, rewrite=False):
        if (rewrite):
            line = '\r' + line
        sys.stdout.write(line + end)
        if (flush):
            sys.stdout.flush()
        self.log(line)

    def error(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents errors.'''
        line = line[:1].upper() + line[1:]
        s = '%s[!] %s%s' % (Colors.R, Utils.to_unicode(line), Colors.N)
        self._display(s, end=end, flush=flush, rewrite=rewrite)

    def output(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents normal output.'''
        s = '%s[*]%s %s' % (Colors.B, Colors.N, Utils.to_unicode(line))
        self._display(s, end=end, flush=flush, rewrite=rewrite)

    def alert(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents important output.'''
        s = '%s[*] %s%s' % (Colors.O, Utils.to_unicode(line), Colors.N)
        self._display(s, end=end, flush=flush, rewrite=rewrite)

    def verbose(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents output if in verbose mode.'''
        if self.VERBOSE:
            self.output("[VERBOSE] " + line, end=end, flush=True, rewrite=rewrite)

    def debug(self, line="", end="\n", flush=True, rewrite=False):
        '''Formats and presents output if in debug mode (very verbose).'''
        if self.DEBUG:
            self.output("[DEBUG]   " + line, end=end, flush=True, rewrite=rewrite)

    def yn(self, line, default=None):
        valid = {"yes": True, "y": True,
                 "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif (default.lower() == "yes") or (default.lower() == "y"):
            prompt = " [Y/n] "
        elif (default.lower() == "no") or (default.lower() == "n"):
            prompt = " [y/N] "
        else:
            self.alert("ERROR: Please provide a valid default value: no, n, yes, y, or None")

        while True:
            choice = self.input(line + prompt)
            if default is not None and choice == '':
                return valid[default.lower()]
            elif choice.lower() in valid:
                return valid[choice.lower()]
            else:
                self.alert("Please respond with 'yes/no' or 'y/n'.")

    def selectlist(self, line, input_list):
        answers = []

        if input_list != []:
            i = 1
            for item in input_list:
                self.output(str(i) + ": " + str(item))
                i = i + 1
        else:
            return answers

        choice = self.input(line)
        if not choice:
            return answers

        answers = (choice.replace(' ', '')).split(',')
        return answers

    def input(self, line):
        '''Formats and presents an input request to the user'''
        s = '%s[?]%s %s' % (Colors.O, Colors.N, Utils.to_unicode(line))
        answer = raw_input(s)
        return answer

    def heading(self, line):
        '''Formats and presents styled header text'''
        line = Utils.to_unicode(line)
        self.output(self.ruler * len(line))
        self.output(line.upper())
        self.output(self.ruler * len(line))

    def print_list(self, title, _list):
        self.heading(title)
        if _list != []:
            for item in _list:
                self.output(item)
        else:
            self.output("None")

# -----------------------------------------------------------------------------
# main test code
# -----------------------------------------------------------------------------
