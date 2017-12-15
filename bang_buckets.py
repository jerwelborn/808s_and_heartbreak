#
# runs on raspberry pi
#
# adapted from hello.txrx.45.py, term.py 
#
#

from bang_buckets_util import *
import time
import serial
from serial import Serial

global filt, eps

def get_signal(board_addr):
      
   byte2 = 0
   byte3 = 0
   byte4 = 0
   ser.flush()


   # while 1:
   #
   # find framing 
   #
   while 1:
      byte1 = byte2
      byte2 = byte3
      byte3 = byte4
      byte4 = ord(ser.read())
      if ((byte1 == 1) & (byte2 == 2) & (byte3 == 3) & (byte4 == 4)):
         break

   # read 
   up_low = ord(ser.read())
   # print "up_load: ", up_low
   up_high = ord(ser.read())
   # print "up_high: ", up_high
   down_low = ord(ser.read())
   # print "down_low: ", down_low
   down_high = ord(ser.read())
   # print "down_high: ", down_high

   up_value = 256*up_high + up_low
   down_value = 256*down_high + down_low
      
   #
   # this is what we're interested in (for detecting a big delta in magnitude)
   # 
   value = (up_value - down_value)
   print "value from board " + str(board_addr) + ": " + str(value)
   # filt = (1-eps)*filt + eps*value
   # print "filtered value: ", filt


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

         get_signal(board_addr)




