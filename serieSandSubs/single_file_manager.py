import sys
import os
import helper
import logging
from config import Config
from configobj import ConfigObj # parse ini files
from configobj import ParseError

class SingleFileManager():
    """
    This class controls the resuming of the single files
    """

    positions_file = None

    def __init__(self, positions_file_name):
        self.positions_file = positions_file_name


    def get_playback_position(self, file_name):
        positions = self.read_positions_file()
        if positions.has_key(file_name) == True:
            pos, length = positions[file_name]
            try:
                return (float(pos), float(length))
            except ValueError as e:
                return 0.0, 0.0
        else:
            return 0.0, 0.0


    def update_playback_position(self, file_name, position, length):
        positions = self.read_positions_file()
        positions[file_name] = position, length
        return self.write_positions_file(positions)


    def get_next_episode(self, file_name):
        config = sys.modules['Config'].get_config()
        try:
            files_in_folder = os.listdir(os.path.dirname(file_name))
        except OSError as e:
            logging.error("SingleFileManager.get_next_episode: " + os.path.dirname(file_name) + " does not exist")
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


    def store_series(self, file_name, add_series=False, persistent=False):
        positions = self.read_positions_file()
        if positions.has_key(file_name) == False:
            positions[file_name] = 0.0, 0.0
        return self.write_positions_file(positions)


    def clean_series_file(self):
        positions = self.read_positions_file()
        for s in positions.copy():
            time = self.get_playback_position(s)
            if time[1] > 0 and (time[1] - time[0]) < 90:
                positions.__delitem__(s)
        return self.write_positions_file(positions)


    def read_positions_file(self):
        try:
            positions = ConfigObj(self.positions_file)
        except ParseError as e:
            logging.critical("SingleFileManager.read_series_file: The file " + positions_file + " is malformed, parsing not possible\n", e)
            helper.clean_and_exit(5)
        return positions


    def write_positions_file(self, instance):
        try:
            instance.write()
        except e:
            logging.critical("SingleFileManager.write_series_file: Can't write the current position into the positions file", e)
            return False
        return True


