"""
   
   808.py 
   Jeremy Welborn
   available at https://github.com/jerwelborn/808s_and_heartbreak
   
   Run a drum machine that records and plays recordings

   To run the system:
   - this runs on a raspberry pi. the sensor boards could have been replaced by sensors off of the pi's GPIO pins. But I was interested in 
   working with AVR controllers and interfacing with AVR controllers from a raspberry pi, so that's that.
   - see how this script works using the help flag (-h, --help) at the command-line
   - documentation, datasheets are available at http://fab.cba.mit.edu/classes/863.17/Harvard/people/jeremywelborn/

   To understand the system:
   - this is redundant with what's on the site referenced above 
   - the RPi talks to AVR boards along a serial bus (an asynchronous serial bus) that is implemented with some like RS-232, RS-422, or RS-485
   - the pattern I've programmed is to ask a specific board for a signal, then wait for that specific board's signal.
   this is because the bus has to be synchronized. the boards only send one byte, so the idea is that the serial tx-rx is sufficiently
   ~fast~ to capture sensor reads! 
   - AHHHH. TOO MANY THOUGHTS.
   - CONCURRENCY BUGS, CONTENTION ON THE BUS, OH MY
      - there's a call to sleep when requesting a signal
      - it is a hacky resolution to a race condition. for awhile, the rpi was WRITING before the bus boards were READING so the boards whose turn it was to send a signal BLOCKED
      - sadly, this is where the system's BOTTLENECK is rn
      
   Acknowledgements: 
   - hello.txrx.45.py (available at http://academy.cba.mit.edu/classes/input_devices/step/hello.txrx.45.py)
   - term.py (available at http://academy.cba.mit.edu/classes/input_devices/python/term.py)
   - python pygame.mixer module -- runs audio asynchrounsly in threads (background threads), so it was simple to overlay sound (speaking too soon???)
      - for me, the alsamixer tool in Linux can be used to control the volume of the system's sound card... 


   Comments / criticisms:
      - software: 
         - some cleanup to the code is required.
      - hardware:
         - what's the extent to which encapsulation (i.e. it is not a big script) ruins timing? 
         - actually, im not sure python is the problem... I think I should try calibrating the ATTiny45's clock  

   How I'm doing audio:
   - This is not really robust at all. 
   - Tried working with python pygame, which has an api for mixing, mixing channels, etc. and allows spinning up sounds in background threads. 
     This worked well in *recording* (when I was having pygame spin up these threads from the foreground(?)) but not in *playing back the recording*. 
     That's because I had to do this in a separate thread (thread of execution, so a thread or a process) so I could be checking the state signal. 
      With threads, there was audio but I couldn't terminate the thread. With processes, there was no audio but I could terminate the thread. I'm not 
      totally comfortable with python concurrency, and was experimenting with fork / exec and examining the state of the sound card... no success. 
   - At any rate, I got it "working" by forking a separate process (with Multiprocessing) and using sub-processes (with subprocess, subprocess.Popen) to 
      run a shell tool called sox or sound exchange (a media manipulation utility, like imagemagick or ffmpeg for audio). This is HUGELY HACKY and not spending 
      any addition time on this rn. 
   - But as I said when I started with pygame, I'm not trying to do any robust audio. That is, I'm relying on the fact that the sensors / the way in which 
     I'm reading sensors does not allow rapid rhythms (this is a drum machine for bass and snare beats!) 
   - I'm simply saving timestamps of when drums had been hit, then I can reply with something like...

         curr = start 
         for sound, timestamp in recording:
            time.sleep(timestamp - curr) 
            sound.sound() 
            curr = timestamp

   TODO:
      - since this has become a toy to record beats / loop recorded beats... assume user only hits one drum at a time...
         1. right now, I do try to avoid bus contention
         2. suppose I do not try to avoid bus contention (b/c of assumption), then have sensor boards send whenever they want. should raise the responsiveness!?
      - "nice to have" not "need to have" features
         - LEDs to convey state - doing this for Tuesday
         - buttons to change sounds, control sound volume - not doing this for Tuesday, sort of annoying to synchronize but revisit this!
            - for what it's worth...
                  - amixer, alsamixer are command-line mixing consoles i.e. mixers for the ALSA sound card driver
                  - alsamixer has a terminal-based GUI for amixer
                  - run something like amixer -M set PCM 50% to set the volume at 50%
      - run on boot

"""

from bang_buckets_util import *
import RPi.GPIO as GPIO
import time, serial, pygame, os
import numpy as np
from serial import Serial

from multiprocessing import Process
# from threading import Thread
import subprocess

class Raspberry_808():

   # samples
   # can add control for these another time
   acoustic = ["kick-acoustic01", "snare-acoustic01", "tom-acoustic01", "hihat-acoustic01", "openhat-acoustic01", "ride-acoustic02", "crash-acoustic"]
   electro = ["kick-electro01", "kick-electro02", "snare-electro", "hihat-electro"]
   roland_808 = ["clap-808", "cowbell-808", "crash-808", "hihat-808", "kick-808", "openhat-808", "perc-808", "snare-808", "tom-808"]

   def __init__(self, port, baudrate, n_boards, sleep_time): 
      
      ## command-line args
      self.ser = serial.Serial(port, baudrate) # has a (composition), is a (inheritance)
      self.n_boards = n_boards # num boards on bus
      self.sleep_time = sleep_time
      
      ## sensor, state information
      self.threshold_vals = {} # { 'board_add' : { 'baseline' : baseline, 'delta' : delta } }
      self.tuning_iters = 5
      self.state = 0
      self.state_indicators = [31,33,35,37] # physical GPIO pin numbers for state-signaling LEDs
      self.display_setup()

      ## sound
      self.recording_start = 0
      self.recording = [] # 2-tuples of (board_addr, timestamp)

      self.sounds = ["kick-808", "snare-808", "clap-808"] # ["kick-acoustic01", "snare-acoustic01", hihat-acoustic01"]

      self.volume = "50%" 

      
   """
      
      talking to sensor boards on bus
      helper functions for everything else to transmit and receieve on the bus

   """
   def request_sensor_signal(self, board_addr):

      self.ser.write(str(board_addr))

   def read_sensor_signal(self, board_addr):
      """
         reads serially from serial port
         computes converted step response val which we'll be treating as arbitary (interested in value delta not value)
      """

      byte2, byte3, byte4, = 0, 0, 0
      self.ser.flush()

      # find framing 
      while 1:
         byte1 = byte2
         byte2 = byte3
         byte3 = byte4
         byte4 = ord(self.ser.read())
         if ((byte1 == 1) & (byte2 == 2) & (byte3 == 3) & (byte4 == 4)):
            break

      # read 
      up_low = ord(self.ser.read())
      up_high = ord(self.ser.read())
      down_low = ord(self.ser.read())
      down_high = ord(self.ser.read())
      up_value = 256*up_high + up_low
      down_value = 256*down_high + down_low
         
      # this is what we're interested in (for detecting a big delta in magnitude)
      value = (up_value - down_value)
      return value 
   
   """

      tuning sensor boards on bus
   
   """
   def tune_board(self, board_addr):
      """
         reads signals (iters signals) from board with address board_addr
         returns average (i.e. baseline) and transformation of std_dev (i.e. threshold)
         called prior to polling in main loop
      """ 
      
      print "\ntuning signal from board " + str(board_addr) + "...\n" 

      adc_readings = []
      # call for data
      for _ in range(self.tuning_iters):

         time.sleep(self.sleep_time) # see main loop 
         
         self.request_sensor_signal(board_addr)
         
         val = self.read_sensor_signal(board_addr)
         print "read from board " + str(board_addr) + ": " + str(val)
         
         adc_readings.append(val)

      # compute baseline, threshold
      baseline = np.average(adc_readings)
      delta = 2000 # np.std(adc_readings) # TODO, PASS AS A PARAMETER FROM USER?

      self.threshold_vals[board_addr] = {'baseline' : baseline, 'delta' : delta}


   def tune_boards(self):
      for board_addr in range(self.n_boards):      
         self.tune_board(board_addr)
   
   """
   
      running system

   """

   def run_808(self):
      """
         runs as as simple state machine 
         state is encapsulated in self.state 

            waiting to record (state == 0) --> recording (state == 1)
                     ^                                    |
                     |                                    v
            playing back (state == 3)  <-- waiting to playback (state == 2)
      
         the beauty of this implementation is that all the avr boards run the same code with no changes (apart from their addresses), although 
         this is no real accomplishment considering I could do this whole thing without controllers off of the raspberry pi... oh well...

         TODO
         add a state == 4 for changing sounds, changing sound volume
         sort of a hack solution but don't wanna deal with synchronizing with the start / stop board rn

      """
      while 1:
         """
         
            STATE 0: waiting to record
         
         """
         if self.state == 0:
            self.display_state()
            print "\n WAITING TO RECORD \n"

            # wait on start / stop button signal 
            self.wait_for_start_stop_signal()

         """
            
            STATE 1: recording
         
         """
         elif self.state == 1:
            self.display_state()
            print "\n RECORDING \n"
            #
            # poll all boards on bus (start / stop sensor board to stop the recording, sound sensor boards to record)
            #
            self.recording_start = time.time()
            self.recording = []

            while 1:
               for board_addr in range(self.n_boards):
                  val = self.request_and_read_signal(board_addr)

                  if self.got_hit(board_addr, val):
      
                     if board_addr != 0: 
                        print "** hit board " + str(board_addr) + " **"
                        
                        # should abstract this away
                        subprocess.Popen(["play", "/home/pi/samples/" + self.sounds[board_addr-1] + ".ogg"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        self.recording.append( (board_addr, time.time()) )

                     else: 
                        self.state = 2 # not calling advanced_state for clarity with successive break
                        break
               if self.state == 2:
                  break

         """
          
          STATE 2: waiting to play back
         
         """
         elif self.state == 2:
            self.display_state()
            print "\n WAITING TO PLAY BACK \n"

            # wait on start / stop button signal
            self.wait_for_start_stop_signal()

         """
         
         STATE 3: playing back
         
         """
         # elif self.state == 3:
         else:
            self.display_state()
            print "\n PLAYING BACK \n"
            
            # spin up recording in a separate thread
            # do this in a thread - same address space so should work out well...           
            playback_thread = Process(target=playback_process_task,
                                       args=(self.recording, self.recording_start, self.sounds))
            # start in background 
            playback_thread.start()

            # wait on start / stop button signal
            while 1:
               val = self.request_and_read_signal(0)
               if self.got_hit(0, val):
                  self.advance_state()

                  # stop in background
                  playback_thread.terminate()

                  break

         """

         STATE 4: change settings

         """   
         # else: 
            # print "\n CHANGE SETTINGS \n"


   """

      helper functions for run808
   
   """

   def request_and_read_signal(self , board_addr):
      """
         recall, have to ask board one at a time so they're synchronized on the bus
      """
      # avoid a race btw request (from rpi) and response (from sensor)
      if board_addr == 0:
         time.sleep(.1) # not sure if this helps here?
      else:
         time.sleep(self.sleep_time)
      # request reading
      self.request_sensor_signal(board_addr) 
      # receive reading
      return self.read_sensor_signal(board_addr)

   def got_hit(self, board_addr, val):
      if abs(val - self.threshold_vals[0]['baseline']) > self.threshold_vals[0]['delta']:
         print "\tdelta from baseline: ",  abs(val - self.threshold_vals[0]['baseline']) 
         return 1
      return 0
      # return abs(val - self.threshold_vals[0]['baseline']) > self.threshold_vals[0]['delta']

   def advance_state(self):
      """
         step through the states
      """
      self.state = (self.state + 1) % 4

   def wait_for_start_stop_signal(self):
      """
      """
      while 1:
         val = self.request_and_read_signal(0)
         if self.got_hit(0, val):
            self.advance_state()
            break   

   def play(self):
      """
         abstract away audio in state 1 (recording)
         TODO
      """
      pass
   
   def playback(self):
      """
         abstract away audio in state 3 (playing back recording)
         TODO
      """
      pass

   def display_setup(self):      
      """
      """      
      GPIO.setmode(GPIO.BOARD) # use physical pin numbers
      for state_indicator in self.state_indicators:
         GPIO.setup(state_indicator, GPIO.OUT)
         GPIO.output(state_indicator, GPIO.LOW)

   def display_state(self):
      """
      """
      # turn off LED 
      GPIO.output(self.state_indicators[(self.state - 1) % 4], GPIO.LOW)
      # turn on LED 
      GPIO.output(self.state_indicators[self.state], GPIO.HIGH)

def playback_process_task(recording, recording_start, sounds):
   """
      runnable 
   """
   while 1:
      curr = recording_start
      for sound, timestamp in recording:
         time.sleep(timestamp - curr)
         print timestamp - curr
         subprocess.Popen(["play", "/home/pi/samples/" + sounds[sound-1] + ".ogg"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
         curr = timestamp 

"""

   run as a raspberry pi script

"""
if __name__ == "__main__":

   args = build_cli().parse_args()
   pi = Raspberry_808(args.port, args.baudrate, args.n_boards, args.sleep_time)
   
   print "\n########################################" # 40 char
   print "tuning the sensors..."
   print "########################################" 
   
   pi.tune_boards()

   print "\n########################################" # 40 char
   print "running the wanna-be roland..."
   print "########################################" 

   pi.run_808()

   