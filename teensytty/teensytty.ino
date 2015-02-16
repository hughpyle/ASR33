
/**
 * Teletype Model 33 USB driver using Teensy 3
 *
 * ASR33 teletype connects to the hardware serial port, via 20mA current-loop.
 * USB serial connects to the host system.
 * This driver performs character translation and other functions.
 */


// TODO 'esc' may be codepoint 126, check & send as modern ESC


// The teletype's serial interface is a 20mA current loop:
//   110 baud
//   One start bit
//   7 data bits
//   Even parity (one bit)
//   Two stop bits
// So the total frame size is 11 bits.
//
// The UART does not have direct support for even parity plus two stop bits.
// But it does have '9-bit word'.  The Teensy serial code has format SERIAL_8N2
// to use this and set the 9th bit as a stop bit.  Then we can calculate
// the parity bit ourselves when sending to the tty (and ignore parity, or
// clear tha parity bit, when receiving).
// (All Teensy UART modes provide the start bit automatically).
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

// set to add some debug messages to the USB serial port
// #define DEBUG_ALL

// set for "local" testing (USB-only; e.g. `sudo cu -l cu.usbmodem63191`)
// #define TESTING

#ifdef TESTING
#define HWSERIAL Serial
#else
// set this to the hardware serial port being used for the TTY
#define HWSERIAL Serial1
#endif

// set these to the appropriate mode selector pins (DIP switch to ground)
#define PIN_TX_UCLC        2
#define PIN_TX_FOLDSLASH   3
#define PIN_TX_UTF8ARROWS  4
#define PIN_TX_SPARE2      5
#define PIN_RX_NLCR        7
#define PIN_RX_EVENPARITY  8
#define PIN_RX_DELAYS      9
#define PIN_RX_SPARE2      10

// Pushbutton for sending test sequences (momentary switch to ground)
#define PIN_PUSH_TEST    12

#define PIN_INTERNAL_LED 13

#define CR '\r'
#define LF '\n'

bool isTxUCLC;
bool isTxFoldSlash;
bool isTxUtf8Arrows;
bool isRxNLCR;
bool isRxEvenParity;
bool isRxDelays;

int prevUSBByte;
int prevTTYByte;
bool isEscapingTTY;

void setup() {
  // Digital selector pins use input pullups, and dip-switch to ground
  // Note this means (on = feature activated = digital input low)
  pinMode(PIN_TX_UCLC,       INPUT_PULLUP);
  pinMode(PIN_TX_FOLDSLASH,  INPUT_PULLUP);
  pinMode(PIN_TX_UTF8ARROWS, INPUT_PULLUP);
  pinMode(PIN_RX_NLCR,       INPUT_PULLUP);
  pinMode(PIN_RX_EVENPARITY, INPUT_PULLUP);
  pinMode(PIN_RX_DELAYS,     INPUT_PULLUP);

  // Test pushbutton is to ground
  pinMode(PIN_PUSH_TEST,     INPUT_PULLUP);

  // Internal LED is used as a signal
  pinMode(PIN_INTERNAL_LED,  OUTPUT);

  // USB is always at full speed
  Serial.begin(9600);

#ifndef TESTING
  // TTY is 110 baud, 8-bit-word, two stop bits, no parity
  HWSERIAL.begin(110, SERIAL_8N2);
#endif
}


// ---- main loop

void loop() {
  int incomingByte;

  if (!digitalRead(PIN_PUSH_TEST)) {
    digitalWrite(PIN_INTERNAL_LED, HIGH);
    selfTest();
  }
  digitalWrite(PIN_INTERNAL_LED, LOW);

  isTxUCLC       = !digitalRead(PIN_TX_UCLC);
  isTxFoldSlash  = !digitalRead(PIN_TX_FOLDSLASH);
  isTxUtf8Arrows = !digitalRead(PIN_TX_UTF8ARROWS);
  isRxNLCR       = !digitalRead(PIN_RX_NLCR);
  isRxEvenParity = !digitalRead(PIN_RX_EVENPARITY);
  isRxDelays     = !digitalRead(PIN_RX_DELAYS);

  if (HWSERIAL.available() > 0) {
    incomingByte = HWSERIAL.read();
    incomingByte = processTTYByte(incomingByte);
  }

  if (Serial.available() > 0) {
    incomingByte = Serial.read();
    incomingByte = processUSBByte(incomingByte);
  }

}


// ---- Bytes from USB to TTY

int processUSBByte(int b)
{
#ifdef DEBUG_ALL
    Serial.print("Received from USB: ");
    Serial.write(b);
    Serial.print("= 0x");
    Serial.println(b, HEX);
#endif

    if (isRxNLCR) {
      // Linefeed conversion, incoming LF => send CR+LF to teletype
      if ((b==LF) && (prevUSBByte!=CR)) {
        // write a CR first
        sendToTTY(CR);
      }
    }

    prevUSBByte = b;
    sendToTTY(b);
    return b;
}


void printTTY(const char *s) {
  // Print a string to the teletype
  for(int i=0; i<strlen(s); s++) {
    sendToTTY(s[i]);
  }
}


void sendToTTY(int b) {
  // Print a character to the teletype
  // Includes appropriate parity and delays
  bool pbit = 1;
  if (isRxEvenParity) {
    pbit = parity(b);
#ifdef DEBUG_ALL
    Serial.print("Parity ");
    Serial.println(pbit, DEC);
#endif
  }
  // TODO set the parity bit

  HWSERIAL.write(b);

  if (isRxDelays) {
    if (b==CR) {
      // Add delay after carriage return
      delay(250);
    }
    if (b==LF) {
      // Add delay after line feed
      delay(200);
    }
  }

#ifdef TESTING
  delay(20);
#endif
}


// ---- Bytes from TTY to USB

int processTTYByte(int b) {
  int c = b;
#ifdef DEBUG_ALL
  Serial.print("Received from TTY: ");
  Serial.write(b);
  Serial.print("= 0x");
  Serial.println(b, HEX);
#endif

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

  prevTTYByte = b;
  sendToUSB(c);
  return c;
}


void sendToUSB(int c) {
  // Print a character to the USB port
  if (c>0) {
    Serial.write(c);
  }
}


// ---- Misc

bool parity(uint8_t v) {
  // Compute the parity bit
  bool p = false;
  while (v) {
    p = !p;
    v &= v - 1; // clear the least significant bit set
  }
  return p;
}


char *yesno(bool f) {
  if (f) return "yes";
  return "no";
}


// ----- Self-test routines ----------------------------------------------------
//
// Inspired by the DEC PDP teletype tests
// http://bitsavers.trailing-edge.com/pdf/dec/pdp8/diag/MAINDEC-08-D2QD-D.pdf

int options = 0;
int prevOptions = -1;
int testMode = 1;

void selfTest() {

  options = isTxUCLC + (isTxFoldSlash<<1) + (isTxUtf8Arrows<<2)
            + (isRxNLCR<<4) + (isRxEvenParity<<5) + (isRxDelays<<6);
  if (options==prevOptions) {
    testMode++;
  } else {
    Serial.print("Tx UC->LC fold? ");  Serial.println(yesno(isTxUCLC));
    Serial.print("Tx Fold escape? ");  Serial.println(yesno(isTxFoldSlash));
    Serial.print("Tx UTF8 arrows? ");  Serial.println(yesno(isTxUtf8Arrows));
    Serial.print("Rx LF -> CR+LF? ");  Serial.println(yesno(isRxNLCR));
    Serial.print("Rx Even Parity? ");  Serial.println(yesno(isRxEvenParity));
    Serial.print("Rx CRLF Delays? ");  Serial.println(yesno(isRxDelays));
  }
  prevOptions = options;

  // "0        1         2         3         4         5         6         7  "
  // "123456789012345678901234567890123456789012345678901234567890123456789012"
  //
  switch(testMode) {
    case 1:
      // Just type all the standard printable characters.
      printTTY("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!\"#$%&^()*+,-./:;<=>?@[\]^_\r\n");
      break;

    case 2:
      // Right-margin test
      // (note: the final dash is beyond position 72, should overstrike the final I)
      printTTY("----I----I----I----I----I----I----I----I----I----I----I----I----I----I-I-\r\n");
      break;

    case 3:
      // Space test
      printTTY(" / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / / /\r");
      for (int i=0; i<72; i+=2) {
        for (int j=0; j<i; j++) {
          sendToTTY(' ');
        }
        sendToTTY('\\');
        sendToTTY(CR);
      }
      sendToTTY(LF);
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
      testMode = 0;
      break;
  }
  delay(500);
}
