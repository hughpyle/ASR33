
/**
 * Teletype Model 33 USB driver using Teensy 3.0
 *
 * ASR33 teletype connects to the hardware serial port, via 20mA current-loop.
 * USB serial connects to the host system.
 * This driver performs character translation and other functions.
 * 
 * NB depends on a hacked AltSoftSerial:
 * https://github.com/hughpyle/AltSoftSerial/tree/hacking
 * 
 * 2018-09-03 update for with arduino 1.8.6
 */

// TODO:
// - handle BREAK: after a short break, send Ctrl+C / flush incoming
// - handle BREAK: after a long break, reset the USB
// - some set of ANSI (vt52? vt100?) escape sequences
//    e.g. those supported by LA34/LA36/LA120
//    http://bitsavers.trailing-edge.com/www.computer.museum.uq.edu.au/pdf/EK-LA34S-TM-001%20DECwriter%20IV%20Series%20Technical%20Manual.pdf
// http://www.inwap.com/pdp10/ansicode.txt
// - turn on and off the VT125 printer (punch tape)
//      [4i = Received data goes to VT102 screen, not to its printer
//      [5i = Received data goes to VT102's printer, not its screen
//   or [@R -> 022 12 R DC2	Device Control 2, causes ASR-33 to activate paper-tape reader
//      [@T -> 024 14 T DC4	Device Control 4, causes ASR-33 to deactivate paper-tape reader
//      (similarly for ENQ, XON, etc)
// - switch in and out of "raw binary mode" (for punch tape)?
//      [@P => DLE? & ETB
// - escapes for turning auto line-wrapping on and off
//      [?7h = DECAWM - AutoWrap Mode, start newline after column 80
//      [?7l = DECAWM - Cursor remains at end of line after column 80


// ===========================================================================

// The teletype's serial interface is a 20mA current loop:
//   110 baud
//   "mark" when not transmitting
//   One start bit (space)
//   7 data bits
//   Even parity (one bit, mark)
//   Two stop bits (mark)
// So the total frame size is 11 bits.
//
// The Teensy has great UARTs but they can't run slowly enough and also do USB.
// (You can underclock, or use the UARTs at >500 baud, but not down to 110).
// So instead this uses a software serial driver (AltSoftSerial).
//
// ASR33 is 7-bit ASCII, which does not include lowercase letters.
// But for terminals and generally, lowercase is more useful (for example,
// all the unix system commands as well as most usernames are lowercase).
// With linux, you want to `stty tty33`, or `stty opost onlcr iuclc cr1 nl1`
// - post-process output
// - translate newline to carriage return + newline
// - translate upper-case characters to lower-case
// - delay after carriage-return and line-feed to let the terminal catch up.
//
// But modern kernels (e.g. Darwin) have removed support for some of these stty
// options, so it's more convenient and more flexible to do here in firmware.
//
// The ASR33's ASCII (ANSI X3.4-1963) differs from today's ASCII in other ways.
// Codepoint 0x5e is "up arrow", not caret (^).
// - A good Unicode representation is 0x2191, or UTF8 \xE2\x86\x91
// Codepoint 0x5f is "back arrow", not underscore.
// - A good Unicode representation is 0x2190, or UTF8 \xE2\x86\x90
// Codepoints in the extended set (0x60 to 0x7e) are not available because the
// high bit is for parity.  These codepoints include the lowercase alphabet,
// backtick (`), curly braces ({}), vertical bar (|) and tilde (~).
//
// This driver adds features for tx (from TTY to host) and rx (from host)
// and controls them with DIP toggle switches.
//   tx: Downcase ASCII uppercase letters.
//   tx: foldcase when '\' precedes alpha
//       (so \L becomes uppercase if downcasing, or lowercase if not)
//
//   rx: convert all plain NL to CR+NL
//   rx: send the tty even-parity (off = send 'mark parity')
//   rx: add delays after carriage-return and newline
//
// Additionally there's a pushbutton that triggers various test sequences.

// ===========================================================================

// Test Setup instructions (OSX):
// - Assume Arduino 1.8.6 and Teensyduino are installed.
// - In the Arduino UI:
//      Tools -> Board -> Teensy 3.0
//      Tools -> USB type -> Serial
// - Verify and upload to the teensy controller.
// - Still in the arduino UI, choose the serial port
//      Tools -> Port -> /dev/cu.usbmodemNNN
// - Then you should be able to run,
//      Tools -> Serial Monitor

// ===========================================================================

// ASR33 terminal strip 3 & 4 are "tty send"
// - data sent from the teletype, which is not polarity sensitive
// - keyboard and tape reader
// - connect these to the "Rx" (teensy input)
//
// ASR33 terminal strip 6 (neg) & 7 (pos) are "tty rcv"
// - data received by teletype
// - printer and tape punch
// - connect these to "Tx" (teensy output)

// ===========================================================================

//#define CONFIG_TIMER_PRESCALE_256
#include <AltSoftSerial.h>

// pin 20 receive
// pin 21 transmit

// Uncomment this to run with "debug" messages.  It prints various "helpful" messages to the
// USB serial port to help with debugging the code.
// #define DEBUG_ALL

// Uncomment this to run "testing mode": development without a tty attached
// #define TESTING

#ifdef TESTING
#define HWSERIAL Serial
#else
// Use the modified AltSoftSerial with inverted data frame
AltSoftSerial altSerial(1,1,true);
#define HWSERIAL altSerial
#endif

// set these to the appropriate mode selector pins (DIP switch to ground)
#define PIN_TX_UCLC        2
#define PIN_TX_FOLDSLASH   3
#define PIN_TX_UTF8ARROWS  4
#define PIN_TX_8BITCLEAN   5
#define PIN_RX_8BITCLEAN   7
#define PIN_RX_NLCR        8
#define PIN_RX_EVENPARITY  9
#define PIN_RX_DELAYS      10

// Pushbutton for sending test sequences (momentary switch to ground)
#define PIN_PUSH_TEST      11
#define PIN_PUSH_SPARE     12

#define PIN_INTERNAL_LED 13

#define CR '\r'
#define LF '\n'

// You can tweak the baud rate very slightly here, but it's better to use 110 and
// fix whatever timing/alignment issues in hardware
#define BAUDRATE 111

#define SNOOZETIME 5000
elapsedMillis millisSinceActivity;


// Pressing he "test pushbutton" runs a series of printer tests,
// each press cycles to the next one. 
// testId is the ID of the currently-running test.
int testId = 0;

bool isTestMode;
bool isTxUCLC;
bool isTxFoldSlash;
bool isTxUtf8Arrows;
bool isTx8BitClean;
bool isRxNLCR;
bool isRxEvenParity;
bool isRxDelays;
bool isRx8BitClean;

int prevUSBByte;
int prevTTYByte;
bool isEscapingTTY;

void setup() {
  // Digital selector pins use input pullups, and dip-switch to ground
  // Note this means (on = feature activated = digital input low)
  pinMode(PIN_TX_UCLC,       INPUT_PULLUP);
  pinMode(PIN_TX_FOLDSLASH,  INPUT_PULLUP);
  pinMode(PIN_TX_UTF8ARROWS, INPUT_PULLUP);
  pinMode(PIN_TX_8BITCLEAN,  INPUT_PULLUP);
  pinMode(PIN_RX_NLCR,       INPUT_PULLUP);
  pinMode(PIN_RX_EVENPARITY, INPUT_PULLUP);
  pinMode(PIN_RX_DELAYS,     INPUT_PULLUP);
  pinMode(PIN_RX_8BITCLEAN,  INPUT_PULLUP);

  // Test pushbutton is to ground
  pinMode(PIN_PUSH_TEST,     INPUT_PULLUP);
  pinMode(PIN_PUSH_SPARE,    INPUT_PULLUP);

  // Internal LED is used as a signal
  pinMode(PIN_INTERNAL_LED,  OUTPUT);

  // USB is always at full speed
  Serial.begin(9600);

#ifndef TESTING
  // TTY is 110 baud, 8-bit-word, two stop bits, no parity
  HWSERIAL.begin(BAUDRATE); //, SERIAL_8N2);
#endif

  millisSinceActivity = SNOOZETIME;
  readOptions();
}


// ---- main loop

void loop() {
  int incomingByte;

  if (isTestMode) {
    // print a test sequence
    selfTest();
  }
  
  if (Serial.available() > 0) {
    // Print something to tty
    incomingByte = Serial.read();
    incomingByte = processUSBByte(incomingByte);
    sendToTTY(incomingByte);
    millisSinceActivity = 0;
  } else if (HWSERIAL.available() > 0) {
    // Read something from tty
    incomingByte = HWSERIAL.read();
    incomingByte = processTTYByte(incomingByte);
    millisSinceActivity = 0;
  } else if (millisSinceActivity > SNOOZETIME) {
    // Stop the open-line chattering
    HWSERIAL.setBreak();
  } else {
    // Keep the line open so timing errors are minimized
    sendToTTY(0);
  }


}


void readOptions() {
  isTestMode     = !digitalRead(PIN_PUSH_TEST);
  isTxUCLC       = !digitalRead(PIN_TX_UCLC);
  isTxFoldSlash  = !digitalRead(PIN_TX_FOLDSLASH);
  isTxUtf8Arrows = !digitalRead(PIN_TX_UTF8ARROWS);
  isTx8BitClean  = !digitalRead(PIN_TX_8BITCLEAN);
  isRxNLCR       = !digitalRead(PIN_RX_NLCR);
  isRxEvenParity = !digitalRead(PIN_RX_EVENPARITY);
  isRxDelays     = !digitalRead(PIN_RX_DELAYS);
  isRx8BitClean  = !digitalRead(PIN_RX_8BITCLEAN);

#ifdef DEBUG_ALL
  Serial.print("Tx 8-bit clean? ");  Serial.println(yesno(isTx8BitClean));
  if (!isTx8BitClean) {
    Serial.print("Tx UC->LC fold? ");  Serial.println(yesno(isTxUCLC));
    Serial.print("Tx Fold escape? ");  Serial.println(yesno(isTxFoldSlash));
    Serial.print("Tx UTF8 arrows? ");  Serial.println(yesno(isTxUtf8Arrows));
  }
  Serial.print("Rx LF -> CR+LF? ");  Serial.println(yesno(isRxNLCR));
  Serial.print("Rx Even Parity? ");  Serial.println(yesno(isRxEvenParity));
  Serial.print("Rx CRLF Delays? ");  Serial.println(yesno(isRxDelays));
  Serial.print("Rx 8-bit clean? ");  Serial.println(yesno(isRx8BitClean));
#endif
}


// ---- Bytes from TTY to USB

void printTTY(const char *s) {
  for(uint i=0; i<strlen(s); s++) {
    sendToTTY(s[i]);
  }
}


int processUSBByte(int b)
{
#ifdef DEBUG_ALL
  Serial.print("Received from USB: ");
  Serial.write(b);
  Serial.print(" = 0x");
  Serial.println(b, HEX);
#endif

  if (!isRx8BitClean) {
    if (isRxNLCR) {
      // TODO linefeed conversion, LF => CR+LF
      if ((b==LF) && (prevUSBByte!=CR)) {
        // write a CR first
        sendToTTY(CR);
      }
    }
  }

  prevUSBByte = b;
  //sendToTTY(b);
  return b;
}


void sendToTTY(int b) {

  if (!isRx8BitClean) {
    // When sending to the tty, normally the parity bit will be set '1'
    // Optionally can set even-parity
    bool pbit = 1;
    if (isRxEvenParity) {
      pbit = parity(b);
#ifdef DEBUG_ALL
//    Serial.print("Parity ");
//    Serial.println(pbit, DEC);
#endif
    }
    // TODO set the parity bit
  }

#ifdef DEBUG_ALL
  if(b!=0) {
    Serial.print("Sending to TTY: ");
    Serial.write(b);
    Serial.print(" = 0x");
    Serial.println(b, HEX);
  }
#endif

  // Print the received byte at the teletype
  // HWSERIAL.flush();
  digitalWrite(PIN_INTERNAL_LED, HIGH);
  HWSERIAL.write(b);
  while (HWSERIAL.isWriting()) {}
  digitalWrite(PIN_INTERNAL_LED, LOW);
  delay(1);

  // CR/LF delays apply even on the 8-bit-clean path
  if (isRxDelays) {
    if (b==CR) {
      // Add delay after carriage return (200m or more)
      sendToTTY(0);
      sendToTTY(0);
    }
    if (b==LF) {
      // Add delay after line feed
      sendToTTY(0);
    }
  }

#ifdef TESTING
  delay(20);
#endif
}


int processTTYByte(int b) {
  int c = b;

#ifdef DEBUG_ALL
  Serial.print("Received from TTY: ");
  Serial.write(b);
  Serial.print(" = 0x");
  Serial.print(b, HEX);
  Serial.print(" = ");
  Serial.println(c, BIN);
#endif

  if (!isTx8BitClean) {
    // Processing

    // Ryemove the parity bit
    b = b & 0x7F;
    c = b;

    if(isTxUCLC) {
      // TTY produces uppercase alpha, fold them to lowercase
      if (b>='A' && b<='Z') {
        c = b + ('a' - 'A');
      }
    }
  
    if (isTxUtf8Arrows) {
      if (b=='\x5E') {
        // caret => up arrow
        sendToUSB('\xE2');
        sendToUSB('\x86');
        c = '\x90';
      }
      if (b=='\x5F') {
        // underscore => left arrow
        sendToUSB('\xE2');
        sendToUSB('\x86');
        c = '\x91';
      }
    }
  
    // \n -> N
    // \7 -> \7
    // \\ -> \\ (and no escaping of the next character)
    if (isTxFoldSlash) {
      if (isEscapingTTY) {
        // Previous character was backslash (and was not sent).
        // It might 'escape' the current character.
        if (c>='A' && c<='Z') {
          // The current character is uppercase alpha, send as lowercase
          c = c + ('a' - 'A');
        } else if (c>='a' && c<='z') {
          // The current character is lowercase alpha, send as uppercase
          c = c - ('a' - 'A');
        } else {
          // Otherwise: send the slash and then the current character unchanged
          sendToUSB(prevTTYByte);
        }
        isEscapingTTY = false;
      } else if (b=='\x5C') {
        // This is a backslash.  Don't send it yet.
        isEscapingTTY = true;
        c = -1;
      }
    }
  }

  prevTTYByte = b;

  // Don't send nulls to the USB terminal
  if (c != 0) {
    sendToUSB(c);
  }
  return c;
}

void sendToUSB(int c) {
  if (c>0) {
    Serial.write(c);
  }
}


bool parity(uint8_t v) {
  bool p = false;
  while (v) {
    p = !p;
    v &= v - 1; // clear the least significant bit set
  }
  return p;
}


const char *yesno(bool f) {
  if (f) return "yes";
  return "no";
}


// ----- Self-test routines ----------------------------------------------------
//
// Inspired by the DEC PDP teletype tests
// http://bitsavers.trailing-edge.com/pdf/dec/pdp8/diag/MAINDEC-08-D2QD-D.pdf

int options = 0;
int prevOptions = -1;

void selfTest() {

  readOptions();
  options = isTxUCLC + (isTxFoldSlash<<1) + (isTxUtf8Arrows<<2)
            + (isRxNLCR<<4) + (isRxEvenParity<<5) + (isRxDelays<<6);
  if (options==prevOptions) {
    // start the next test
    testId++;
  } else {
    // the DIP-switches are changed, start the tests over
    testId = 1;
  }
  prevOptions = options;

  // "0        1         2         3         4         5         6         7  "
  // "123456789012345678901234567890123456789012345678901234567890123456789012"
  //
  switch(testId) {
    case 1:
      // Just type all the standard printable characters.
      printTTY("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\"#$%&^()*+,-./:;<=>?@[]^_\r\n");
      break;

    case 2:
      // Right-margin test
      // (note: the final dash is beyond position 72, should overstrike the final I)
      printTTY("----I----I----I----I----I----I----I----I----I----I----I----I----I----I-I-\r\n");
      break;

    case 3:
      // Space test
      printTTY(" / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / /\r\n");
      //for (int i=0; i<72; i+=2) {
      //  for (int j=0; j<i; j++) {
      //    sendToTTY(' ');
      //  }
      //  sendToTTY('\\');
      //  sendToTTY(CR);
      //}
      //sendToTTY(LF);
      break;

    case 4:
      // Carriage return test
      // For N from 71 down to 10: print asterisk at position N,
      // then CR, then number at position 1.
      for (int i=71; i>10; i--) {
        for (int j=0; j<i; j++) {
          sendToTTY(' ');
        }
        sendToTTY('*');
        sendToTTY(CR);
        sendToTTY('0' + (i % 10));
        sendToTTY(CR);
        sendToTTY(LF);
      }
      break;

    case 5:
      // Print 6 lines of the ASR33 WORST CASE PATTERN, which consists of
      // (octal) 047, 137, 127, 057, 127, 137
      // (hex)   x27, x5F, x57, x2F, x57, x5F
      // (apostrophe) (left-arrow) W (slash) W (left-arrow)
      for(int i=1; i<=6; i++) {
        sendToTTY('\047');
        sendToTTY('\137');
        sendToTTY('\127');
        sendToTTY('\057');
        sendToTTY('\127');
        sendToTTY('\137');
        printTTY("\r\n");
      }
      break;

    default:
      printTTY("Tests complete.\r\n");
      testId = 0;
      break;
  }
  delay(500);
}
