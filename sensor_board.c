#define board_addr '2'
// should be updated for each board along the serial bus
// have this here so I can do this in a script

/*
      
   sensor-board.c | Jeremy Welborn | jeremywelborn@college.harvard.edu | 12/12/17

   adapted from (1) hello.txrx.45.c and (2) hello.bus.45.c by Neil Gershenfeld
   (1) available at http://academy.cba.mit.edu/classes/input_devices/step/hello.txrx.45.c
   (2) available at http://academy.cba.mit.edu/classes/networking_communications/bus/hello.bus.45.c
   
   adapted to abstract away ADC for step response, configuring the correct parameters in particular
   for serial communication
   
   step response is 9600 baud 
   serial bus is 9600 baud 

   pinout:
                          |-------|
                 RST/PB5 -| 1   8 |- VCC
   Rx step sensor -- PB3 -| 2   7 |- PB2/SCK   -- driving debugging LED 
   Tx step sensor -- PB4 -| 3   6 |- PB1/MISO  -- Rx on serial bus, also for FTDI interface
                     GND -| 4   5 |- PB0/MOSI  -- Tx on serial bus
                          |-------|

   --------------------------------------------------------------------------------

   background on AVR programming, I/O pins and ports for the reader:
    
   ATtiny45 controls other components on the board (i.e. does I/O) 
   by sending and receiving serial (0 / 0 V or 1 / 5 V) signals. These signals are 
   recieved and sent by reading and writing to "pins," which are arranged in "ports," 
   which have a small set of registers. 

   The registers for a port define how the pins for that port behave:
      - set pins as input pins or output pins via the DDRx or Data Direction Register 
        for port x (e.g. `DDRA = 0x0F; // 1st 4 pins on port A are outputs (can write to them), 2nd 4 pins on port A are inputs (can read from them))
      - write to output pins via the PORTx or Data Register for port x (e.g. PORTA = OxFF; 
        // write 1's to the output pins of port A)
      - read from input pins via the PINx or Port Input Pins for port x  
    

 */ 

#include <avr/io.h> // macros for port / pin namespace
#include <util/delay.h>
#include <stdlib.h>

#define output(directions,pin) (directions |= pin) // set port direction for output
#define input(directions,pin) (directions &= (~pin)) // set port direction for input
#define set(port,pin) (port |= pin) // set port pin
#define clear(port,pin) (port &= (~pin)) // clear port pin
#define pin_test(pins,pin) (pins & pin) // test for port pin
#define bit_test(byte,bit) (byte & (1 << bit)) // test for bit set

/* Neil did these on a scope, trying not to reproduce that */
#define bit_delay_time 102 // bit delay for 9600 with overhead
#define bit_delay() _delay_us(bit_delay_time) // RS232 bit delay
#define half_bit_delay() _delay_us(bit_delay_time/2) // RS232 half bit delay
#define settle_delay() _delay_us(100) // settle delay
#define char_delay() _delay_ms(10) // char delay
#define nloop 100 // loops to accumulate

/* 

   pin, port macros 

*/ 

/* def for diode */
#define led_port PORTB
#define led_data_direction DDRB
#define led_pin (1 << PB2)

/* defs for serial bus */
// serial_in_pin i.e. Tx    ASK WHY IN IS TX AND OUT IS RX? IS IT W.R.T. THE BUS?
// serial_out_pin i.e. Rx
#define serial_direction DDRB
#define serial_out_register PORTB // Neil calls this serial_port 
#define serial_in_register PINB  // Neil calls this serial_pins, which is misleading to me 
#define serial_out_pin (1 << PB1) 
#define serial_in_pin (1 << PB0)


/* defs for sensor */
// don't have to touch PB3 this is used by ADC 
#define sensor_tx_port PORTB
#define sensor_tx_direction DDRB
#define sensor_tx_pin (1 << PB4) 


/*

   prototypes (functions aren't hoisted here!)

 */

struct adc_result {
   uint16_t up;
   uint16_t down;
};
typedef struct adc_result adc_result;

void send_serial(adc_result* adc_res);
void adc_setup();
void adc_sense(adc_result* adc_res);
void get_char(volatile unsigned char *pins, unsigned char pin, char *rxbyte);
void put_char(volatile unsigned char *port, unsigned char pin, char txchar);


/********************************************************************************




   main 




 ********************************************************************************/ 



int main(void) {
   
   // read raspberry pi's requeted board address into this char
   static char board_addr_req;

   // set clock divider to /1
   CLKPR = (1 << CLKPCE);
   CLKPR = (0 << CLKPS3) | (0 << CLKPS2) | (0 << CLKPS1) | (0 << CLKPS0);
   
   // initialize pins / ports
   set(serial_out_register, serial_out_pin); // write 1 to PB2 
   input(serial_direction, serial_out_pin); // PB2 should be listening on bus
   
   clear(sensor_tx_port, sensor_tx_pin); // write 0 to PB4
   output(sensor_tx_direction, sensor_tx_pin); // PB4 is output pin
   
   set(led_port, led_pin);
   output(led_data_direction, led_pin);

   /* initialize ADC */
   // set up registers
   adc_setup();
   // set up struct to store results
   adc_result* adc_res = (adc_result*) malloc(sizeof(adc_result));


   /* repeatedly sense and send */ 
   while (1) {
   
      // reset reading
      adc_res->up = 0;
      adc_res->down = 0;

      /*
          
          TODO experiment with how this is gonna go...

       */ 

      // read requested board from rpi
      get_char(&serial_in_register, serial_in_pin, &board_addr_req);
      
      // // if this is the board the rpi has requested a signal from...
      if ((board_addr == (char) board_addr_req)) {

         // allow writing to the bus
         output(serial_direction, serial_out_pin);

         // turn on the LED for debugging
         clear(led_port, led_pin);
         
         // store analog signal in adc_res struct
         adc_sense(adc_res);
     
         // send result of analog-to-digital conversion
         // relying on Neil's implementation and abstracting this away!!
         send_serial(adc_res);

         // back to listening on the bus
         input(serial_direction, serial_out_pin);

         // turn off the LED
         set(led_port, led_pin);
         
      }
   }
}




/******************************************************************************** 




   helper functions




 ********************************************************************************/ 

/**
 * send_serial
 * 
 * wraps up Neil's implementation of this particular async protocol
 *
 * macros need not be passed as params
 *
 */
void send_serial(adc_result* adc_res) { 
   // send framing
   put_char(&serial_out_register, serial_out_pin, 1);
   char_delay();
   put_char(&serial_out_register, serial_out_pin, 2);
   char_delay();
   put_char(&serial_out_register, serial_out_pin, 3);
   char_delay();
   put_char(&serial_out_register, serial_out_pin, 4);
   
   /*
      I've read off of the python script that's reading the results to see
      what these represent... 

      see lines 40s-50s of the script to see the computation (magnitude computation)
    */

   // send result
   put_char(&serial_out_register, serial_out_pin, (adc_res->up & 255));
   char_delay();
   put_char(&serial_out_register, serial_out_pin, ((adc_res->up >> 8) & 255));
   char_delay();
   put_char(&serial_out_register, serial_out_pin, (adc_res->down & 255));
   char_delay();
   put_char(&serial_out_register, serial_out_pin, ((adc_res->down >> 8) & 255));
   char_delay();
}


void adc_setup() {
   ADMUX = (0 << REFS2) | (0 << REFS1) | (0 << REFS0) // Vcc ref
      | (0 << ADLAR) // right adjust
      | (0 << MUX3) | (0 << MUX2) | (1 << MUX1) | (1 << MUX0); // PB3
   ADCSRA = (1 << ADEN) // enable
      | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0); // prescaler /128
   
}

void adc_sense(adc_result* adc_res) { 
   
   unsigned char count;

   // accumulate signal
   // adc_res->up = 0;
   // adc_res->down = 0;
   // doing this in main loop for clarity rn

   for (count = 0; count < nloop; ++count) { 
      
      // settle, charge
      settle_delay();
      set(sensor_tx_port, sensor_tx_pin); // write 5V to tx pad
      
      // initiate conversion
      ADCSRA |= (1 << ADSC);
      
      // wait for completion
      while (ADCSRA & (1 << ADSC)) {}

      // save result
      adc_res->up += ADC;
      
      // settle, discharge
      settle_delay();
      clear(sensor_tx_port, sensor_tx_pin);
      
      // initiate conversion
      ADCSRA |= (1 << ADSC);
      
      // wait for completion
      while (ADCSRA & (1 << ADSC)) {}
      
      // save result
      adc_res->down += ADC;
   }
}


/**
 * get_char -- this is Neil's implementation
 */
void get_char(volatile unsigned char *pins, unsigned char pin, char *rxbyte) {
   //
   // read character into rxbyte on pins pin
   //    assumes line driver (inverts bits)
   //
   *rxbyte = 0;
   while (pin_test(*pins,pin))
      //
      // wait for start bit
      //
      ;
   //
   // delay to middle of first data bit
   //
   half_bit_delay();
   bit_delay();
   //
   // unrolled loop to read data bits
   //
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 0);
   else
      *rxbyte |= (0 << 0);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 1);
   else
      *rxbyte |= (0 << 1);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 2);
   else
      *rxbyte |= (0 << 2);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 3);
   else
      *rxbyte |= (0 << 3);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 4);
   else
      *rxbyte |= (0 << 4);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 5);
   else
      *rxbyte |= (0 << 5);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 6);
   else
      *rxbyte |= (0 << 6);
   bit_delay();
   if pin_test(*pins,pin)
      *rxbyte |= (1 << 7);
   else
      *rxbyte |= (0 << 7);
   //
   // wait for stop bit
   //
   bit_delay();
   half_bit_delay();
}


/**
 * put_char - this is Neil's implementation
 */
void put_char(volatile unsigned char *port, unsigned char pin, char txchar) {
   //
   // send character in txchar on port pin
   //    assumes line driver (inverts bits)
   //
   // start bit
   //
   clear(*port,pin);
   bit_delay();
   

   /*
      we want to send txchar
      if bit is set (i.e. is 1) in txchar

      unsure why Neil had this unrolled
    */ 
   /*
   int i; 
   for (i = 0; i < 8; i++) {
      if bit_test(txchar, i)
         set(*port,pin);
      else
         clear(*port,pin);
      bit_delay();      
   }
   */

   if bit_test(txchar, 0)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 1)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 2)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 3)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 4)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 5)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 6)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   if bit_test(txchar, 7)
      set(*port,pin);
   else
      clear(*port,pin);
   bit_delay();      
   //
   // stop bit
   //
   set(*port,pin);
   bit_delay();
   //
   // char delay
   //
   bit_delay();
}
