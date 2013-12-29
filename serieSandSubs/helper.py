from configobj import ConfigObj
from config import Config
import sys, logging, os, time, shutil, subprocess
import magic

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

    # subtitle status
    if cmd == "subtitle_visibility":
        # send the get_time_pos command to the player
        mplayer_cmd = open(config['paths']['mplayer_input'], "w")
        mplayer_cmd.write("pausing_keep_force get_sub_visibility\n")
        mplayer_cmd.close()
        time.sleep(0.1)
        # grep the new player output and parse the subtitle status
        mplayer_output = open(config['paths']['mplayer_output'], "r")
        out = mplayer_output.readlines()
        mplayer_output.close()
        for line in out:
            if line.find("ANS_SUB_VISIBILITY") >= 0:
                try:
                    return int(line.split("=")[1].strip())
                except ValueError as e:
                    return -2

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

    # quit player
    if cmd == "quit":
        mplayer_cmd = open(config['paths']['mplayer_input'], "w")
        mplayer_cmd.write("pausing_keep_force quit\n")
        mplayer_cmd.close()
        time.sleep(0.1)
        return 0
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

def strip_html_from_subtitle_file(filename):
    tmp_filename = "temp_subtitle_file"
    new_filename = filename + ".new"
    # try to convert subtitle file encodign to utf-8 if not already done
    # at the moment, we only can do this automatically for ISO-8859-1 encodings
    encoding = magic.from_file(filename).lower()
    if encoding.find("utf-8") >= 0:
        try:
            shutil.copy(filename, tmp_filename)
        except IOError as e:
            logging.critical("Can't copy the subtitle file, no write permission")
            clean_and_exit(3)
    elif encoding.find("iso-8859") >= 0:
        # cause we cant detect exact encoding, ISO-8859-1 is used
        subprocess.call(["iconv", "-f", "ISO-8859-1", "-t", "UTF-8", filename, "-o", tmp_filename])
        if os.path.exists(tmp_filename) == False:
            logging.critical("Error during subtitle file conversion")
            clean_and_exit(3)
    else:
        logging.critical("The subtitle file has an unknown encoding. Please convert first")
        clean_and_exit(3)
    # next, read subtitle file and add a backslash at every line end
    # that's a preparation for the html stripping done by pandoc later
    subtitles_with_backslash = ""
    subfile = open(tmp_filename)
    while True:
        line = subfile.readline()
        if line == "":
            break
        line = line.replace("`","'")
        line = line.replace("$","Dollar ")
        line = line.strip()
        subtitles_with_backslash += "%s\\\n" % line
    subfile.close()
    subfile = open(tmp_filename, "w")
    subfile.write(subtitles_with_backslash)
    subfile.close()
    # next, call pandoc to do the html tag stripping
    subprocess.call(["pandoc", "-t", "plain", "-o", new_filename, tmp_filename])
    if os.path.exists(new_filename) == False:
        logging.critical("Can't strip html tags from subtitle file")
        clean_and_exit(3)
    # pandoc creates two spaces at every line end --> strip them
    subtitles_without_spaces = ""
    subfile = open(new_filename)
    while True:
        line = subfile.readline()
        if line == "":
            break
        subtitles_without_spaces += "%s\n" % line.strip()
    subfile.close()
    subfile = open(new_filename, "w")
    subfile.write(subtitles_without_spaces)
    subfile.close()
    # lastly we rename the files
    # keep original subtitle file and delete temp file
    os.remove(tmp_filename)
    os.rename(filename, filename+".original")
    os.rename(new_filename, filename)

