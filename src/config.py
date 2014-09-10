from configobj import ConfigObj
from configobj import ParseError
import helper
import os
import sys
import tty
import logging

class Config():
    """
    This class contains a parser for the config file and a getter and setter
    """
    config = None

    def __init__(self):
        tty.setcbreak(sys.stdin)
        # start the logger
        logging.basicConfig(level=logging.WARNING, format='%(levelname)-8s %(message)s')
        # parse the config file
        self.config = self.parse_config_file()

    def get_config(self):
        return self.config

    def parse_config_file(self):
        """
        create the settings folder and load the preferences
        the settings folder is ~/.mplayer which already should be created by the mplayer
        the config file name is serieSandSubs.conf
        """
        logging.info("start config file parsing")
        settings_folder = os.path.expanduser("~") + "/.mplayer/"
        if os.path.exists(settings_folder) == False or os.path.isdir(settings_folder) == False:
            try:
                os.mkdir(settings_folder)
            except OSError as e:
                logging.critical("The settings folder " + settings_folder + " could not be created")
                helper.clean_and_exit(2)
        # load the config file
        config_file = settings_folder + "serieSandSubs.conf"
        if os.path.exists(config_file) == False:
            logging.critical("The config file " + config_file + " must be created first")
            helper.clean_and_exit(2)
        try:
            config = ConfigObj(config_file)
        except ParseError as e:
            logging.critical("The config file " + config_file + " could not be parsed\n", e)
            helper.clean_and_exit(2)

        # check if all necessary data is specified
        # general section
        if config.has_key("general") == False:
            logging.critical("Error in the config file: The general section is missing")
            helper.clean_and_exit(2)
        if config['general'].has_key("activate subtitles") == False:
            config['general']['activate subtitles'] = "yes"
        if config['general'].has_key("activate remember positions") == False:
            config['general']['activate remember positions'] = "yes"

        # media manager
        config['media_manager']['instance'] = None
        config['media_manager']['end_of_video'] = False
        config['media_manager']['sleep_timer'] = False
        config['media_manager']['closed_by_sleep_timer'] = False
        if config['media_manager'].has_key("series file types") == False:
            config['media_manager']['series file types'] = [ "avi", "mpg", "mkv", "m4a" ]
        try:
            config['media_manager']['sleep time interval'] = int(config['media_manager']['sleep time interval'])
        except ValueError as e:
            config['media_manager']['sleep time interval'] = 5
        except KeyError as e:
            config['media_manager']['sleep time interval'] = 5
        try:
            config['media_manager']['pause between continuous playback'] = int(config['media_manager']['pause between continuous playback'])
        except ValueError as e:
            config['media_manager']['pause between continuous playback'] = 10
        except KeyError as e:
            config['media_manager']['pause between continuous playback'] = 10

        # subtitles section
        if config['general']['activate subtitles'].lower() == "yes":
            if config.has_key("subtitles") == False:
                logging.critical("Error in the config file: The subtitles section is missing")
                helper.clean_and_exit(2)
            if config['subtitles'].has_key("sender name") == False:
                logging.critical("Error in the config file: No sender name for the jabber account")
                helper.clean_and_exit(2)
            if config['subtitles'].has_key("sender password") == False:
                logging.critical("Error in the config file: No sender password for the jabber account")
                helper.clean_and_exit(2)
            if config['subtitles'].has_key("recipients") == False:
                logging.critical("Error in the config file: No recipients specified")
                helper.clean_and_exit(2)
        # subtitle instance
        config['subtitles']['instance'] = None
        config['subtitles']['delay'] = 0.0

        # add a few internal used paths to the config dictionary
        # no need to put them in the config file
        config['paths'] = {}
        config['paths']['single_pos_file'] = settings_folder + "single_file_positions"
        config['paths']['series_file'] = settings_folder + "series_file"
        config['paths']['mplayer_input'] = "/tmp/mplayer_control"
        config['paths']['mplayer_output'] = "/tmp/mplayer_output"
        config['paths']['full_media_file'] = ""
        config['paths']['beep'] = settings_folder + "beep.ogg"
        return config


