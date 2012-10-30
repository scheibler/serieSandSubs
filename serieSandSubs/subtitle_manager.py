import sleekxmpp
import magic        # find out encoding of text files
import logging
import codecs
import sys
import time

class SubtitleManager(sleekxmpp.ClientXMPP):

    """
    A XMPP message sender
    """

    subtitles = []

    def __init__(self, jid, password, subtitle_filename):
        # make a jabber client instance
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        # load the subtitle file and parse it's contents
        self.subtitles = self.parse_subtitle_file(subtitle_filename)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can intialize
        # our roster.
        self.add_event_handler("session_start", self.start)

        # load a few sleekxmpp plugins
        self.registerPlugin('xep_0030')
        self.registerPlugin('xep_0199')
        if self.connect():
            self.process()
            time.sleep(1)
        else:
            logging.critical("Can't connect to the jabber server")
            helper.clean_and_exit(3)


    def start(self, event):
        """
        Process the session_start event.
        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.getRoster()
        self.sendPresence()

    def parse_subtitle_file(self, sub_filename):
        """
        parse the entries in the subtitle file into an array
        at the moment, the method can convert .srt files with the following structure:
            1 (subtitle index)
            00:00:01,234 --> 00:12,345
            An example subtitle
            over more than one line
            which is separated by an empty line

        """
        sub_array = []
        found_time = False
        i = 0
    
        encoding = magic.from_file(sub_filename)
        if encoding.find("ISO-8859") >= 0:
            encoding = "ISO-8859-1"
        else:
            encoding = encoding.split(" ")[0]
        try:
            sub_file = codecs.open(sub_filename, "r", encoding)
        except IOError as e:
            logging.critical("Can't open the subtitle file\n", e)
            helper.clean_and_exit(3)
        except LookupError as e:
            logging.warning("Encoding of the subtitle file could not be detected\nTry to open it with UTF-8 encoding")
            sub_file = codecs.open(sub_filename, "r", "UTF-8")
        line = sub_file.readline()
        error_counter = 0
        while line:
            line = line.strip()
            if found_time == True:
                if line == "":
                    found_time = False
                    i = i+1
                else:
                    sub_array[i][2] = sub_array[i][2].__add__(line + " ")
            if line.count(":") == 4 and line.find("-->") > 0:
                times = line.strip().split(" --> ")
                try:
                    start = self.transform_time(times[0])
                    end = self.transform_time(times[1])
                except:
                    logging.warning("Could not parse the subtitle file ", sub_filename, "\nError in the line ", line, " (subtitle ", i+1, ")\n")
                    if error_counter >= 10:
                        logging.critical("Too many errors in the subtitle file")
                        helper.clean_and_exit(3)
                    error_counter = error_counter +1
                sub_array.append([start, end, ""])
                found_time = True
            line = sub_file.readline()
        sub_file.close()
        return sub_array

    def transform_time(self, time):
        """
        Helper function to convert time string into seconds
        example for input = '00:12:09,210'
        returns float
        """
        try:
            t = time.split(":")
            hour = int(t[0])
            min = int(t[1])
            t = t[2].split(",")
            sec = int(t[0])
            milli = int(t[1][0])
        except e:
            raise
        return hour*3600 + min*60 + sec + milli*0.1

    def get_current_subtitle(self, current_pos):
        """
        This method returns the current subtitle from the subtitle array
        current_pos is a float and contains the current video position in seconds
        if no subtitle exists, an empty string is returned
        """
        i = 0
        while i < self.subtitles.__len__():
            if i > 0:
                if current_pos >= self.subtitles[i-1][1] and current_pos < self.subtitles[i][0]:
                    return ""
            if current_pos >= self.subtitles[i][0] and current_pos < self.subtitles[i][1]:
                return self.subtitles[i][2]
            i = i+1
        return ""

    def send_msg(self, recipients, message):
        """
        sends the given message
        if recipients is a list, every the message will be send to every entry
        otherwise recipients only contains one recipient (string)
        """
        if type(recipients) == type([]):
            for r in recipients:
                if r != "":
                    self.send_message(mto=r, mbody=message, mtype='chat')
        else:
            self.send_message(mto=recipients, mbody=message, mtype='chat')

    def end(self):
        self.disconnect(wait=True)

