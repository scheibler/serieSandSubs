#!/usr/bin/env python

import subprocess
import os
import sys
import time
import thread
import argparse # parse the command line parameters
import string
import re       # regex
import select
import logging

# non standard librarys
from subtitle_manager import SubtitleManager
from series_manager import SeriesManager
from single_file_manager import SingleFileManager
from config import Config
import helper
from configobj import ConfigObj # parse ini files


# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')

def control_background_process():
    """
    Control the subtitle sending and the position remembering
    This method is started in an own thread and runs in parallel to the MPlayer
    """
    config = sys.modules['Config'].get_config()
    if config['subtitles']['instance'] == None:
        show_subtitles = False
    else: 
        show_subtitles = True

    # print start message
    # get video length
    parsing_error_counter = 0
    video_length = 0
    while True:
        video_length = helper.send_command_to_mplayer("videolength")
        if video_length > 0:
            parsing_error_counter = 0
            break
        if parsing_error_counter >= 5:
            logging.critical("Can't get the length of the video file, MPlayer not accessible")
            helper.clean_and_exit(1)
        parsing_error_counter = parsing_error_counter +1
        time.sleep(5)
    # get video artist
    video_artist = None
    parsing_error_counter = 0
    while True:
        video_artist = helper.send_command_to_mplayer("get_artist")
        if type(video_artist) == type("") or video_artist == None:
            parsing_error_counter = 0
            break
        if parsing_error_counter >= 20:
            logging.critical("Can't get the artist of the video file, MPlayer not accessible.")
            helper.clean_and_exit(1)
        parsing_error_counter = parsing_error_counter +1
        time.sleep(0.5)
    parsing_error_counter = 0
    video_title = None
    while True:
        video_title = helper.send_command_to_mplayer("get_title")
        if type(video_title) == type("") or video_title == None:
            parsing_error_counter = 0
            break
        if parsing_error_counter >= 10:
            logging.critical("Can't get the title of the video file")
            helper.clean_and_exit(1)
        parsing_error_counter = parsing_error_counter +1
        time.sleep(0.5)

    print "Playing: " + config['paths']['full_media_file']
    if video_title != None and video_artist != None:
        print "Artist: %s\nTitle: %s\nLength: %.2d:%.2d" % (video_artist, video_title, video_length/60, video_length%60)
    elif video_title != None:
        print "Title: %s\nLength: %.2d:%.2d" % (video_title, video_length/60, video_length%60)
    else:
        print "Title: %s\nLength: %.2d:%.2d" % (os.path.basename(config['paths']['full_media_file']), video_length/60, video_length%60)
    print "\n"

    old_sub = ""
    last_video_pos = 0
    count_pause_cycles = 0
    print_position = 0
    last_sleep_timer_success = 0
    number_of_beeps = 0
    while True:
        if config['media_manager']['end_of_video'] == True:
            return True
        current_video_pos = helper.send_command_to_mplayer("currentpos")
        subtitle_visibility = helper.send_command_to_mplayer("subtitle_visibility")
        if current_video_pos < 0:
            if parsing_error_counter == 15:
                logging.warning("Can't parse the MPlayer output")
            if parsing_error_counter == 30:
                logging.warning("Still can't parse the MPlayer output")
            if parsing_error_counter == 60:
                logging.critical("Lost the MPlayer access")
                helper.clean_and_exit(1)
            parsing_error_counter = parsing_error_counter +1
            time.sleep(0.5)
            continue
        else:
            parsing_error_counter = 0
        
        # turn on / off subtitles
        if config['subtitles']['instance'] != None:
            if subtitle_visibility == 0 and show_subtitles == True:
                show_subtitles = False
                print "\nsubtitles deactivated"
                config['subtitles']['instance'].send_msg(config['subtitles']['recipients'], "subtitles deactivated")
            if subtitle_visibility == 1 and show_subtitles == False:
                show_subtitles = True
                print "\nsubtitles activated"
                config['subtitles']['instance'].send_msg(config['subtitles']['recipients'], "subtitles activated")

        # sleep timer
        if config['media_manager']['sleep_timer'] == True:
            diff = abs(current_video_pos - last_video_pos)
            # reset if video was paused or user jumped more than 15 seconds
            if diff == 0 or diff > 15:
                last_sleep_timer_success = current_video_pos
                number_of_beeps = 0

            if (last_sleep_timer_success + config['media_manager']['sleep time interval'] * 60 - 30) < current_video_pos and number_of_beeps == 0:
                subprocess.call([mplayer_path, "-quiet", config['paths']['beep']], \
                        stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
                number_of_beeps += 1
            if (last_sleep_timer_success + config['media_manager']['sleep time interval'] * 60 - 20) < current_video_pos and number_of_beeps == 1:
                subprocess.call([mplayer_path, "-quiet", config['paths']['beep']], \
                        stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
                number_of_beeps += 1
            if (last_sleep_timer_success + config['media_manager']['sleep time interval'] * 60 - 10) < current_video_pos and number_of_beeps == 2:
                subprocess.call([mplayer_path, "-quiet", config['paths']['beep']], \
                        stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"))
                number_of_beeps += 1
            if (last_sleep_timer_success + config['media_manager']['sleep time interval'] * 60) < current_video_pos:
                config['media_manager']['closed_by_sleep_timer'] = True
                helper.send_command_to_mplayer("quit")

        # if the file is playing (no pause)
        if current_video_pos - last_video_pos != 0:
            print "\rCurrent position: %.2d:%.2d of %.2d:%.2d (%.1f%%)" % \
                    (current_video_pos/60, current_video_pos%60, \
                    video_length/60, video_length%60, \
                    current_video_pos/video_length*100),; sys.stdout.flush()
            # subtitles
            if show_subtitles == True:
                sub = config['subtitles']['instance'].get_current_subtitle( \
                        current_video_pos - config['subtitles']['delay'])
                if sub != old_sub and sub != "":
                    config['subtitles']['instance'].send_msg(config['subtitles']['recipients'], sub)
                    old_sub = sub
            
            # current video position
            # save the current position every 5 seconds
            if abs(current_video_pos - config['media_manager']['instance'].get_playback_position(config['paths']['full_media_file'])[0]) > 5:
                updated = config['media_manager']['instance'].update_playback_position(config['paths']['full_media_file'], current_video_pos, video_length)
                if updated == False:
                    logging.error("Main.control_background_process: can't write the current playback position")
                    break
            last_video_pos = current_video_pos
        time.sleep(0.33)


########################
# start of the main part
########################
# create the args parser
parser = argparse.ArgumentParser(description="Series manager and XMPP subtitle distributor")
parser.add_argument("-f", "--from-beginning", action="store_true",
                    help="Start the media file from beginning regardless of the possibly remenered position")
parser.add_argument("-s", "--subtitle-file",
                    help="Select a subtitle file. If no file is given the program tries to find a file based on the name of the given media file")
parser.add_argument("-d", "--subtitle-delay",
                    help="Specify a delay in seconds for the subtitles")
parser.add_argument("-a", "--add-series", action="store_true",
                    help="If this option is set, the choosen media file is added as the start point of a series")
parser.add_argument("-p", "--persistent", action="store_true",
                    help="Normally a series is deleted automatically after watching the last episode.\
                            If this option is set, the series entry will persist in the list until it is deleted by the user (only useful with the -a option)")
parser.add_argument("-c", "--continuous-playback", action="store_true",
                    help="Continuous playback of the choosen series")
parser.add_argument("-t", "--sleep-timer", action="store_true",
                    help="Turn on sleep timer. Then you must stop and start the movie at certain \
                    intervals to verify, that you are still awake. Otherwise the playback will stop.")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Shows the error messages of MPlayer and increases the programs output")
parser.add_argument("-V", "--version", action="store_true",
                    help="Get current program version")
parser.add_argument("mediafile", nargs="?", default="",
                    help="specify a media file name or specify parts of a series which should be resumed (must be encloesed in \"\").\
                    If nothing is entered, the program will list all saved series")

# load the config file
sys.modules['Config'] = Config()
config = sys.modules['Config'].get_config()

# check if the mplayer is installed
mplayer_path = string.split(subprocess.check_output(["whereis", "mplayer"]), " ")
try:
    mplayer_path = mplayer_path[1]
except IndexError as e:
    logging.critical("The Mplayer is not installed, please do that first")
    helper.clean_and_exit(1)

# initialize the mplayer command input fifo
mplayer_command_fifo = config['paths']['mplayer_input']
if os.path.exists(mplayer_command_fifo) == False:
    try:
        os.mkfifo(mplayer_command_fifo)
    except OSError as e:
        logging.critical("Can't create Mplayer command input fifo\n" + str(e))
        helper.clean_and_exit(1)

# create Mplayer output file
mplayer_output_filename = config['paths']['mplayer_output']
try:
    mplayer_output_file = open(mplayer_output_filename,"w")
except IOError as e:
    logging.critical("Can't create Mplayer output file\n" + str(e))
    helper.clean_and_exit(1)

# create the file for the series
if os.path.exists(config['paths']['series_file']) == False:
    try:
        last_positions_file = open(config['paths']['series_file'],"w")
        last_positions_file.close()
    except IOError as e:
        logging.critical("Can't create file for the series file\n" + str(e))
        helper.clean_and_exit(1)

# create the file for the single files
if os.path.exists(config['paths']['single_pos_file']) == False:
    try:
        last_positions_file = open(config['paths']['single_pos_file'],"w")
        last_positions_file.close()
    except IOError as e:
        logging.critical("Can't create file for the single file\n" + str(e))
        helper.clean_and_exit(1)


##################################
# parse the command line arguments
args = parser.parse_args()

# version
if args.version == True:
    print "serieSandSubs version 0.2.1"
    helper.clean_and_exit(0)

# verbosity
if args.verbose == True:
    mplayer_error_path = None
    logging.basicConfig(level=logging.INFO)
else:
    mplayer_error_path = open(os.devnull, "w")

# process the entered value for the media file
media_file = args.mediafile

# four possible variants for resuming a series
# 1. The user explicitely wants to add the entered media file as the start point of a series
# the media file exists and the -a flag is set
# then with the "get_current_episode" method get the full path for the media file
# after that save the next episode with the "find_next_episode" method
if args.add_series == True and os.path.isfile(media_file) == True:
    # create the SeriesManager object
    config['media_manager']['instance'] = SeriesManager(config['paths']['series_file'])
    config['media_manager']['instance'].clean_series_file()
    config['paths']['full_media_file'] = os.path.realpath(media_file)
    config['media_manager']['instance'].store_series(config['paths']['full_media_file'], True, args.persistent)
# 2. same situation as in option 1. but the media file does not exist, so exit the program
elif args.add_series == True and os.path.isfile(media_file) == False:
    logging.critical("Adding a new series wwas not possible, file " + media_file + " not found")
    helper.clean_and_exit(1)
# 3. the user don't wants to add a new series but also entered no valid media file
# so the user wants to view the next episode of a saved series
# the system lists all matched series, starts the choosen one and also finds the next episode
elif args.add_series == False and os.path.isfile(media_file) == False:
    # create the SeriesManager object
    config['media_manager']['instance'] = SeriesManager(config['paths']['series_file'])
    config['media_manager']['instance'].clean_series_file()
    config['paths']['full_media_file'] = config['media_manager']['instance'].choose_series(media_file)
    config['media_manager']['instance'].store_series(config['paths']['full_media_file'], False, False)
# 4. no add flag set and valid media file
# system starts the file in the normal mode, no resuming of a series
else:
    # create the single files manager object
    config['media_manager']['instance'] = SingleFileManager(config['paths']['single_pos_file'])
    config['media_manager']['instance'].clean_series_file()
    config['paths']['full_media_file'] = os.path.realpath(media_file)
    config['media_manager']['instance'].store_series(config['paths']['full_media_file'], False, False)

# sleep timer
if args.sleep_timer == True:
    config['media_manager']['sleep_timer'] = True


while True:
    # should the file definitely played from beginning
    # if not, search for a potentially saved position in the remember_last_position file
    if args.from_beginning == True or config['general']['activate remember positions'].lower() == "no":
        start_at = 0
    else:
        start_at = config['media_manager']['instance'].get_playback_position(config['paths']['full_media_file'])[0]

    # subtitle file
    if args.subtitle_file != None:
        subtitle_filename = args.subtitle_file
        if os.path.exists(subtitle_filename) == False:
            logging.critical("The entered subtitle file " + subtitle_filename + " does not exist")
            helper.clean_and_exit(1)
    else:
        media_file_without_ext = os.path.splitext(config['paths']['full_media_file'])
        if os.path.exists(media_file_without_ext[0] + ".srt") == True:
            subtitle_filename = media_file_without_ext[0] + ".srt"
        else:
            subtitle_filename = ""

    if args.subtitle_delay != None:
        try:
            config['subtitles']['delay'] = float(args.subtitle_delay)
        except ValueError as e:
            logging.critical("The subtitle delay must be a float")
            helper.clean_and_exit(1)

    ###########################################
    # create the instance of the subtitles manager
    if subtitle_filename != "" and config['general']['activate subtitles'].lower() == "yes":
        config['subtitles']['instance'] = SubtitleManager(config['subtitles']['sender name'], config['subtitles']['sender password'], subtitle_filename)

    # start the background process
    config['media_manager']['end_of_video'] = False
    thread.start_new_thread(control_background_process, ())

    # start the Mplayer
    try:
        if subtitle_filename == "":
            subprocess.call([mplayer_path, "-af", "scaletempo=scale=1", "-ss", str(start_at),
                            "-quiet", "-input", "file=" + mplayer_command_fifo,
                            "-subdelay", str(config['subtitles']['delay']),
                            config['paths']['full_media_file']],
                            stdout=mplayer_output_file, stderr=mplayer_error_path)
        else:
            subprocess.call([mplayer_path, "-af", "scaletempo=scale=1", "-sub", subtitle_filename,
                            "-ss", str(start_at),"-quiet", "-input", "file=" + mplayer_command_fifo,
                            "-subdelay", str(config['subtitles']['delay']),
                            config['paths']['full_media_file']],
                            stdout=mplayer_output_file, stderr=mplayer_error_path)
    except OSError as e:
        logging.critical("Can't start Mplayer\n" + str(e))
        mplayer_output_file.close()
        helper.clean_and_exit(1)

    config['media_manager']['end_of_video'] = True
    if args.continuous_playback == True and config['media_manager']['closed_by_sleep_timer'] == False:
        print("\nThe next episode starts automatically in %d seconds, press ENTER or Space to begin \
                immediately or press ESC or q to quit: " % config['media_manager']['pause between continuous playback'])
        quit = False
        while True:
            i, o, e = select.select( [sys.stdin], [], [], config['media_manager']['pause between continuous playback'])
            if (i):
                key = ord(sys.stdin.read(1))
                if key == 10 or key == 32:
                    print "OK\n"
                    break
                if key == 113 or key == 27:
                    quit = True
                    break
            else:
                print "OK\n"
                break
        if quit == True:
            break
        current_pos = config['media_manager']['instance'].get_playback_position(config['paths']['full_media_file'])
        if current_pos[1] > 0 and (current_pos[1] - current_pos[0]) < 90:
            config['paths']['full_media_file'] = config['media_manager']['instance'].get_next_episode(config['paths']['full_media_file'])
        config['media_manager']['instance'].clean_series_file()
        if config['paths']['full_media_file'] == None:
            print "No further episodes available"
            break
        else:
            config['media_manager']['instance'].store_series(config['paths']['full_media_file'], False, False)
    else:
        break

# cleanup
mplayer_output_file.close()
helper.clean_and_exit(0)

