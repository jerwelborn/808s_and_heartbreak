"""
   
   bang-buckets.py 
   Jeremy Welborn
   available at https://github.com/jerwelborn/bucket-banging
   

   runs on raspberry pi

   acknowledgements: figured out serial from 
   hello.txrx.45.py (available at http://academy.cba.mit.edu/classes/input_devices/step/hello.txrx.45.py),
   term.py (available at http://academy.cba.mit.edu/classes/input_devices/python/term.py)

   comments:

      - software: 
         - some cleanup to the code is required. 
         - there are some ugly side effects. TODO re-do w/ object-oriented design. would rather have all 
         command-line args as instance vars and to run system.run() or something, this parameter passing (e.g. for ser) is terrible.
      - hardware:
         - what's the extent to which encapsulation (i.e. function calls) ruins timing, could be a bit faster if things 
         like loops were unrolled? but after all I wrote this for the RPi in Python and not in C
         - TODO tune the sleep?
         - actually, im not sure python is the problem...

   comments

   TODO:
   - thresholding function - tune baseline_signal, delta i.e. if abs(signal- baseline_signal) > delta:
   - audio w/ pygame.mixer, pygame.mixer.music which abstracts away of threading, allowing overlay of sound (https://ubuntuforums.org/archive/index.php/t-783317.html)
   - recall, alsamixer can be used to the sound card's volume. should have this high but do volume adjustments with
   pygame proportional to signal - baseline_signal
   - create a list of .wav sounds you like, store those (paths to those) as a global and scp them to the pi
   - button hardware??? do this with a breadboard 1st to see how this affects synchonrization
   - def set_baseline_signals():

      Normalize signals / baseline signals for each board
    write a special char board by board (can't all settle at once, can't share bus)
     rpi should average 1000 signal and store average as baseline, delta as something related to the std dev


"""

from bang_buckets_util import *
import RPi.GPIO as GPIO
import time
import serial
from serial import Serial


# run as a raspberry pi script
if __name__ == "__main__":

   # 
   # extract command-line, set up serial communication
   #
   args = build_cli().parse_args()
   port, baudrate, n_boards, verbose_flag, sleep_time = args.port, args.baudrate, args.n_boards, args.verbose, args.sleep_time

   ser = serial.Serial(port, baudrate)
   ser.setDTR()


   threshold_vals = {}

   #
   # tune the sensors 
   #
   print "\n########################################" # 40 char
   print "tuning the sensors..."
   print "########################################" 
   
   for board_addr in range(n_boards):
      
      baseline, delta = set_baseline_signal(ser, board_addr, 25, verbose_flag, sleep_time)
      
      threshold_vals[board_addr] = {'baseline' : baseline, 'delta' : delta}

   #
   # poll on serial port board by board for their sensor signals
   #

   print "\n########################################" # 40 char
   print "reading the sensors, running the system..."
   print "########################################" 

   while 1:

      # hard-coded for 3 sensor boards on the bus
      # N.B. get_char will block if you don't have the correct number of boards on the bus
      for board_addr in range(3):
         
         # this sleep() call is super important! 
         # I had a classic concurrency bug on the bus. after the 1st time through the loop,
         # the raspberry pi wrote an address before the the sensor boards were reading, so the 
         # boards ended up blocking, waiting for the signal to be sent from the rpi. As a solution,
         # 1. sleep or 2. add some sort of retry logic!!
         #
         # You'll have to tune this!
         time.sleep(sleep_time)

         # poll
         request_sensor_signal(ser, board_addr)

         # process
         val = read_sensor_signal(ser, board_addr)
         print "read from board " + str(board_addr) + ": " + str(val)

         if abs(val - threshold_vals[board_addr]['baseline']) > threshold_vals[board_addr]['delta']:
            print "** got a hit on board " + str(board_addr) + " **"











