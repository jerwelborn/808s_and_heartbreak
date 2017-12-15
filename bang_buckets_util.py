#
# bang-buckets-util.py
#

import argparse

def build_cli():

   desc = '''
            script to run the raspberry pi \n
            polls on the serial port board by board for sensor board signals\n
            thresholds the signal and sends audio over MAX9744 amplifier for BIG sounds\n
            should be run on boot
          '''
   epil = '''
            Written by Jeremy Welborn (github: jerwelborn)
          '''

   parser = argparse.ArgumentParser(description=desc, epilog=epil)
   
   port_arg_help = '''
                  specify the async serial port; on Raspbian (and Unix generally) these are \
                  accessible in the /dev directory (virtual directory) as files to which the \
                  process running this program will "bind" and read from / write to. Woo hoo!

               ''' 
   parser.add_argument('-p', '--port', action='store', default='/dev/ttyS0', help=port_arg_help)
   
   baudrate_arg_help = ''' specify the serial baudrate (bit rate) '''
   parser.add_argument('-b', '--baudrate', action='store', default='9600', help=port_arg_help)

   return parser