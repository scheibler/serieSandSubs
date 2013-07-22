import re       # regex manager
import sys
import os
import helper
import logging
from config import Config
from configobj import ConfigObj # parse ini files
from configobj import ParseError

class SeriesManager():
    """
    This class holds the methos for the series resume feature
    """

    next_episodes_file = None

    def __init__(self, next_episodes_filename):
        self.next_episodes_file = next_episodes_filename

    def choose_series(self, file_name):
        config = sys.modules['Config'].get_config()
        stored_series = self.read_series_file()
        if stored_series.__len__() == 0:
            print "No resumable series available"
            helper.clean_and_exit(4)
        # if the file name is not empty, try to match the entered name against a saved series entry
        # if it's empty list all series, which can be resumed
        if file_name != "":
            regex = re.compile(file_name.replace(" ", ".*"), re.IGNORECASE)
        else:
            regex = re.compile(".*", re.IGNORECASE)
        matched_series = {}
        for s in stored_series:
            if regex.search(s) != None:
                matched_series[s] = stored_series[s]
        if matched_series.__len__() == 0:
            print "No series matches for that input string"
            helper.clean_and_exit(4)
        index = 0
        keys = matched_series.keys()
        keys.sort()
        print "Resumable series:"
        for s in keys:
            index = index+1
            time = self.get_playback_position(matched_series[s]['episode'])
            if time[1] > 0 and (time[1] - time[0]) < 90:
                # next episode
                matched_series[s]['episode'] = self.get_next_episode(matched_series[s]['episode'])
                matched_series[s]['time'] = 0.0, 0.0
                time = 0.0, 0.0
            if s.lower().find("series") >= 0:
                print "%d. %s" % (index, s[s.lower().find("series")+7:].replace("/"," - "))
            elif s.lower().find("serien") >= 0:
                print "%d. %s" % (index, s[s.lower().find("serien")+7:].replace("/"," - "))
            else:
                s_split = s.split("/")
                if s_split.__len__() >= 2:
                    print "%d. %s - %s" % (index, s_split[s_split.__len__()-2], s_split[s_split.__len__()-1])
                else:
                    print "%d. %s" % (index, s)
            if matched_series[s]['episode'] == None:
                print "   Next episode: Currently no episode available\n"
            else:
                pos, of = self.get_file_position(matched_series[s]['episode'])
                if pos == -1:
                    continue
                if time[1] > 0:
                    percent = (time[0]/time[1])*100
                else:
                    percent = 0.0
                if percent > 0.5 and config['general']['activate remember positions'].lower() == "yes":
                    print "   Next episode: %s     %d/%d - %.1f%% played\n" % (os.path.basename(matched_series[s]['episode']), pos, of, percent)
                else:
                    print "   Next episode: %s     %d/%d\n" % (os.path.basename(matched_series[s]['episode']), pos, of)
        if matched_series.__len__() == 1:
            sys.stdout.write("Press enter to load the series or q to quit: ")
        else:
            sys.stdout.write("Enter the index of the seris, which should be played or \"q\" to quit: ")
        
        # parse the user input and return the new media file
        i = -1
        while True:
            key = sys.stdin.read(1)
            # only one series available and the user pressed ENTER to start
            if ord(key) == 10 and matched_series.__len__() == 1 and matched_series[keys[0]]['episode'] != None:
                print "\n"
                return matched_series[keys[0]]['episode']
            # user wants to quit
            if key == "q":
                helper.clean_and_exit(0)
            try:
                key = int(key)
            except ValueError as e:
                continue
            if key > 0 and key <= index and matched_series[keys[key-1]]['episode'] != None:
                print "\n"
                return matched_series[keys[key-1]]['episode']


    def store_series(self, file_name, add_series=False, persistent=False):
        config = sys.modules['Config'].get_config()
        path_name = os.path.dirname(file_name)
        stored_series = self.read_series_file()
        # try to find an entry with the same path as file_name
        time = 0.0, 0.0
        if stored_series.has_key(path_name) == True:
            if add_series == False:
                persistent = stored_series[path_name]['persistent']
            if file_name == stored_series[path_name]['episode']:
                time = stored_series[path_name]['time']
        stored_series[path_name] = {}
        stored_series[path_name]['episode'] = file_name
        stored_series[path_name]['persistent'] = persistent
        stored_series[path_name]['time'] = time
        # save changes
        self.write_series_file(stored_series)
        return True


    def get_next_episode(self, file_name):
        config = sys.modules['Config'].get_config()
        try:
            files_in_folder = os.listdir(os.path.dirname(file_name))
        except OSError as e:
            logging.error("SeriesManager.get_next_episode: " + os.path.dirname(file_name) + " does not exist")
            return None
        filtered_files = []
        for f in files_in_folder:
            for t in config['media_manager']['series file types']:
                if t == os.path.splitext(f.strip())[1].replace(".",""):
                    filtered_files.append(f.strip())
        filtered_files.sort()
        position = 1
        for f in filtered_files:
            if file_name.find(f) >= 0:
                break
            position = position+1
        try:
            return os.path.dirname(file_name) + "/" + filtered_files[position]
        except IndexError as e:
            return None


    def get_playback_position(self, file_name):
        path_name = os.path.dirname(file_name)
        stored_series = self.read_series_file()
        try:
            entry = stored_series[path_name]
        except KeyError as e:
            logging.error("SeriesManager.get_playback_position: The series " + path_name + " does not exist\n" + str(e))
            return 0.0, 0.0
        try:
            if entry['episode'] != file_name:
                logging.warning("SeriesManager.get_playback_position: Episode names don't match\n" + entry['episode'] + " != " + file_name)
                return 0.0, 0.0
            else:
                time = entry['time']
                return (float(time[0]), float(time[1]))
        except KeyError as e:
            logging.error("SeriesManager.get_playback_position: The key does not exist" + str(e))
            return 0.0, 0.0
        except IndexError as e:
            logging.error("SeriesManager.get_playback_position: The time touple is not complete" + str(e))
            return 0.0, 0.0
        except ValueError as e:
            logging.error("SeriesManager.get_playback_position: One of the time values is malformed" + str(e))
            return 0.0, 0.0


    def update_playback_position(self, file_name, position, length):
        path_name = os.path.dirname(file_name)
        stored_series = self.read_series_file()
        try:
            entry = stored_series[path_name]
        except KeyError as e:
            logging.critical("SeriesManager.update_playback_position: The series " + path_name + " does not exist\n" + str(e))
            return False
        try:
            if entry['episode'] != file_name:
                logging.error("SeriesManager.update_playback_position: Episode names don't match\n" + entry['episode'] + " != " + file_name)
                return False
            else:
                entry['time'] = position, length
                return self.write_series_file(stored_series)
        except KeyError as e:
            logging.error("SeriesManager.update_playback_position: The key does not exist" + str(e))
            return False


    def clean_series_file(self):
        stored_series = self.read_series_file()
        for s in stored_series.copy():
            time = self.get_playback_position(stored_series[s]['episode'])
            if time[1] > 0 and (time[1] - time[0]) < 90:
                # try to get the next episode
                next_episode = self.get_next_episode(stored_series[s]['episode'])
                if next_episode == None and stored_series[s]['persistent'] == "False":
                    stored_series.__delitem__(s)
        self.write_series_file(stored_series)


    ####################
    # internal functions
    ####################

    def read_series_file(self):
        config = sys.modules['Config'].get_config()
        try:
            stored_series = ConfigObj(config['paths']['series_file'], indent_type='    ')
        except ParseError as e:
            logging.critical("SeriesManager.read_series_file: The file " + config['paths']['series_file'] + " is malformed, parsing not possible\n" + str(e))
            helper.clean_and_exit(4)
        return stored_series


    def write_series_file(self, instance):
        try:
            instance.write()
        except:
            logging.critical("SeriesManager.write_series_file: Can't write the current position into the stored series file")
            return False
        return True


    def get_file_position(self, file_name):
        config = sys.modules['Config'].get_config()
        try:
            files_in_folder = os.listdir(os.path.dirname(file_name))
        except OSError as e:
            logging.warning("SeriesManager.get_file_position: " + os.path.dirname(file_name) + " does not exist")
            return -1, -1
        filtered_files = []
        for f in files_in_folder:
            for t in config['media_manager']['series file types']:
                if t == os.path.splitext(f.strip())[1].replace(".",""):
                    filtered_files.append(f.strip())
        filtered_files.sort()
        position = 1
        for f in filtered_files:
            if file_name.find(f) >= 0:
                return position, filtered_files.__len__()
            position = position+1
        return 0, filtered_files.__len__()

