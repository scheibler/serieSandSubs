from configobj import ConfigObj
from config import Config
import sys
import os
import time

def send_command_to_mplayer(cmd):
    config = sys.modules['Config'].get_config()
    # first delete the old player output
    mplayer_output = open(config['paths']['mplayer_output'], "w")
    mplayer_output.close()

    # possible commands
    # get artist of file
    if cmd == "get_artist":
        mplayer_cmd = open(config['paths']['mplayer_input'], "w")
        mplayer_cmd.write("pausing_keep_force get_meta_artist\n")
        mplayer_cmd.close()
        time.sleep(0.1)
        # grep the new player output and parse the video length in seconds
        mplayer_output = open(config['paths']['mplayer_output'], "r")
        out = mplayer_output.readlines()
        mplayer_output.close()
        for line in out:
            if line.find("ANS_META_ARTIST") >= 0:
                try:
                    if line.split("=")[1].strip() == "''":
                        return None
                    else:
                        return line.split("=")[1].strip()
                except ValueError as e:
                    return -1
    # get title of file
    if cmd == "get_title":
        mplayer_cmd = open(config['paths']['mplayer_input'], "w")
        mplayer_cmd.write("pausing_keep_force get_meta_title\n")
        mplayer_cmd.close()
        time.sleep(0.1)
        # grep the new player output and parse the video length in seconds
        mplayer_output = open(config['paths']['mplayer_output'], "r")
        out = mplayer_output.readlines()
        mplayer_output.close()
        for line in out:
            if line.find("ANS_META_TITLE") >= 0:
                try:
                    if line.split("=")[1].strip() == "''":
                        return None
                    else:
                        return line.split("=")[1].strip()
                except ValueError as e:
                    return -1
    # length of file
    if cmd == "videolength":
        mplayer_cmd = open(config['paths']['mplayer_input'], "w")
        mplayer_cmd.write("pausing_keep_force get_time_length\n")
        mplayer_cmd.close()
        time.sleep(0.1)
        # grep the new player output and parse the video length in seconds
        mplayer_output = open(config['paths']['mplayer_output'], "r")
        out = mplayer_output.readlines()
        mplayer_output.close()
        for line in out:
            if line.find("ANS_LENGTH") >= 0:
                try:
                    return float(line.split("=")[1].strip())
                except ValueError as e:
                    return -1
    # current file position
    if cmd == "currentpos":
        # send the get_time_pos command to the player
        mplayer_cmd = open(config['paths']['mplayer_input'], "w")
        mplayer_cmd.write("pausing_keep_force get_time_pos\n")
        mplayer_cmd.close()
        time.sleep(0.1)
        # grep the new player output and parse the current video position
        mplayer_output = open(config['paths']['mplayer_output'], "r")
        out = mplayer_output.readlines()
        mplayer_output.close()
        for line in out:
            if line.find("ANS_TIME_POSITION") >= 0:
                try:
                    return float(line.split("=")[1].strip())
                except ValueError as e:
                    return -2
    return -3


def clean_and_exit(exit_code):
    """
    cleans up before exiting
    Error codes:
        0 = all is ok
        1 = errors in the main program
        2. errors in the config class
        3 = errors in the subtitle class
        4. errors in the series manager class
        5 = errors in the single file manager class
    """
    try:
        config = sys.modules['Config'].get_config()
    except KeyError as e:
        sys.exit(exit_code)
    if config['subtitles']['instance'] != None:
        config['subtitles']['instance'].end()
    sys.exit(exit_code)

