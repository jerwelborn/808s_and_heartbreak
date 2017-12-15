"""
    
    bang-buckets-util.py
    Jeremy Welborn
    available at https://github.com/jerwelborn/bucket-banging

"""

import argparse

def build_cli():

   desc = """
            script to run the raspberry pi \n
            polls on the serial port board by board for sensor board signals\n
            thresholds the signal and sends audio over MAX9744 amplifier for BIG sounds\n
            should be run on boot
          """
   epil = """
            Written by Jeremy Welborn (github: jerwelborn)
          """

   parser = argparse.ArgumentParser(description=desc, epilog=epil)
   
   port_arg_help = """                  
                  specify the async serial port; on Raspbian (and Unix generally) these are \
                  accessible in the /dev directory (virtual directory) as files to which the \
                  process running this program will "bind" and read from / write to. Woo hoo!
                  """
                
   parser.add_argument('-p', '--port', action='store', default='/dev/ttyS0', help=port_arg_help)
   
   baudrate_arg_help = """ specify the serial baudrate (bit rate) """
   parser.add_argument('-b', '--baudrate', action='store', default='9600', help=port_arg_help)

   return parser


def read_sensor_signal(board_addr):     
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

