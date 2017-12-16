"""
    
    808-util.py
    Jeremy Welborn
    available at https://github.com/jerwelborn/808s_and_heartbreak

"""

import RPi.GPIO as GPIO
import argparse

def build_cli():

   desc = """
            script to run the raspberry pi 808 ;\n
            see description of states documented in source (808.py)
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
   
   code for control features

"""

def button_setup():
   """
   want to turn on the internal pull-up (or pull-down resistor) for input pin reading a button
   https://learn.sparkfun.com/tutorials/pull-up-resistors
   
   recall, assume a pull-up connecting to 5V 
   if button is pressed, the pin reads 0. if button is not pressed, the pin reads 1.

   i.e. if GPIO.input(button_0): # button on 0 is released
   """   
   
   # 15, 16, 18 are GPIO for buttons
   button_0, button_1 = 15, 16

   GPIO.setmode(GPIO.BOARD) # GPIO.setmode(GPIO.BCM) 
   GPIO.setup(button_0, GPIO.IN, pull_up_down=GPIO.PUD_UP)
   GPIO.setup(button_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_cleanup():
   GPIO.cleanup()

def button_reset():
   """
      should have a button to re-tune the sensors
   """
   pass


