"""
    
    bang-buckets-util.py
    Jeremy Welborn
    available at https://github.com/jerwelborn/bucket-banging

"""

import argparse, time
import numpy as np

def build_cli():

   desc = """
            script to run the raspberry pi;\n
            polls on the serial port board by board for sensor board signals;\n
            thresholds the signal and sends audio over MAX9744 amplifier for BIG sounds;\n
            should be run on boot;
          """
   epil = """
            Written by Jeremy Welborn (github: jerwelborn)
          """

   parser = argparse.ArgumentParser(description=desc, epilog=epil)
   
   port_arg_help =   """                  
                     specify the serial port; on Raspbian (and Unix generally) these are \
                     accessible in the /dev directory (virtual directory) as files to which the \
                     process running this program will "bind" and read from / write to. Woo hoo!
                     """
                
   parser.add_argument('-p', '--port', action='store', default='/dev/ttyS0', help=port_arg_help)
   
   baudrate_arg_help = """ specify the serial baudrate (bit rate) """
   parser.add_argument('-b', '--baudrate', action='store', type=int, default='9600', help=baudrate_arg_help)


   n_boards_arg_help = """ specify the number of boards on bus """
   parser.add_argument('-n', '--n_boards', action='store', type=int, default='3', help=n_boards_arg_help)

   time_arg_help =   """ 
                     specify the time to wait for sensor-board.c to stop writing the bus and to start reading the bus \
                     so there's no race. this isn't an ideal implementation but you'll have to tune this for 
                     reasonable responsiveness. default (slow default) is 0.01.
                     """
   parser.add_argument('-s', '--sleep_time', action='store', type=float, default='0.01', help=time_arg_help)

   verbose_arg_help = """write to the python process's stdout on system behavior"""
   parser.add_argument('-v', '--verbose', action='store', type=int, default='1', help=verbose_arg_help)   

   return parser


"""
   
   talking to boards on the bus

"""

def request_sensor_signal(ser, board_addr):
   """
      wrapped this in a function for readability but experiment to see if overhead of changing 
      instruction pointer for a call is bad for synchronization
   """
   ser.write(str(board_addr)) # what's being written is a str in term.py

def read_sensor_signal(ser, board_addr):     
   """
      reads serially from serial port
      computes converted step response val which we'll be treating as arbitary 
      (interested in value delta not value)
   """

   byte2, byte3, byte4, = 0, 0, 0
   ser.flush()

   # find framing 
   while 1:
      byte1 = byte2
      byte2 = byte3
      byte3 = byte4
      byte4 = ord(ser.read())
      if ((byte1 == 1) & (byte2 == 2) & (byte3 == 3) & (byte4 == 4)):
         break

   # read 
   up_low = ord(ser.read())
   up_high = ord(ser.read())
   down_low = ord(ser.read())
   down_high = ord(ser.read())
   up_value = 256*up_high + up_low
   down_value = 256*down_high + down_low
      
   # this is what we're interested in (for detecting a big delta in magnitude)
   value = (up_value - down_value)
   return value 

def set_baseline_signal(ser, board_addr, iters, verbose_flag, sleep_time):
   """
      reads signals (iters signals) from board with address board_addr
      returns average (i.e. baseline) and transformation of std_dev (i.e. threshold)
      called prior to polling in main loop
   """ 

   if verbose_flag:
      print "\ntuning signal from board " + str(board_addr) + "...\n" 

   adc_readings = []

   # call for data
   for _ in range(iters):   
      time.sleep(sleep_time) # see main loop 
      request_sensor_signal(ser, board_addr)
      
      val = read_sensor_signal(ser, board_addr)
      
      if verbose_flag: 
         print "read from board " + str(board_addr) + ": " + str(val)
      
      adc_readings.append(val)

   # compute baseline, threshold
   baseline = np.average(adc_readings)
   delta = 250 # np.std(adc_readings)

   # play some pygame sound to announce that we're done tuning

   return baseline, delta


"""
   
   buttons

"""

def button_setup():
   """
   want to turn on the internal pull-up (or pull-down resistor) for input pin reading a button
   https://learn.sparkfun.com/tutorials/pull-up-resistors
   recall, if button is pressed, the pin reads 0. if button is not pressed, the pin reads 1.

   i.e. if GPIO.input(button_0): # button on 0 is released
   """   
   
   # 15, 16, 18 are GPIO for buttons
   button_0, button_1, button_2 = 15, 16, 18

   GPIO.setmode(GPIO.BOARD) # GPIO.setmode(GPIO.BCM) 
   GPIO.setup(button_0, GPIO.IN, pull_up_down=GPIO.PUD_UP)
   GPIO.setup(button_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
   GPIO.setup(button_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_cleanup():
   GPIO.cleanup()

def button_reset():
   """
      should have a button to re-tune the sensors
   """
   pass

