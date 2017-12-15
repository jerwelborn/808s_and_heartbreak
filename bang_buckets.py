"""
   
   bang-buckets.py 
   Jeremy Welborn
   available at https://github.com/jerwelborn/bucket-banging
   

   runs on raspberry pi

   acknowledgements: figured out serial from 
   hello.txrx.45.py (available at http://academy.cba.mit.edu/classes/input_devices/step/hello.txrx.45.py),
   term.py (available at http://academy.cba.mit.edu/classes/input_devices/python/term.py)


   TODO:
   - thresholding function - tune baseline_signal, delta i.e. if abs(signal- baseline_signal) > delta:
   - audio w/ pygame.mixer, pygame.mixer.music which abstracts away of threading, allowing overlay of sound
   - recall, alsamixer can be used to the sound card's volume. should have this high but do volume adjustments with
   pygame proportional to signal - baseline_signal
   - button hardware??? do this with a breadboard 1st to see how this affects synchonrization

"""

from bang_buckets_util import *
import RPi.GPIO as GPIO
import time
import serial
from serial import Serial


# run as a raspberry pi script
if __name__ == "__main__":

   # extract from command-line
   args = build_cli().parse_args()
   port, baudrate = args.port, args.baudrate

   ser = serial.Serial(port,9600)
   ser.setDTR()

   while 1:

      # hard-coded for sensor 3 boards on the bus
      # N.B. get_char will block if you don't have the correct number of boards on the bus
      for board_addr in range(3):
         
         
         # this sleep() call is super important! 
         # I had a classic concurrency bug on the bus. after the 1st time through the loop,
         # the raspberry pi wrote an address before the the sensor boards were reading, so the 
         # boards ended up blocking, waiting for the signal to be sent from the rpi. As a solution,
         # 1. sleep or 2. add some sort of retry logic!!
         #
         # You'll have to tune this!
         time.sleep(0.01)

         ser.write(str(board_addr)) # what's being written is a str in term.py

         val = get_signal(board_addr)
         print "value from board " + str(board_addr) + ": " + str(val)







