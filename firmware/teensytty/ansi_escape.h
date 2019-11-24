/*
 * Copyright (c) Hugh Pyle
 * 
 * ansi_escape.h
 * Defines a class that can process ANSI/vt100-style escape sequences for a teletype ASR33.
 */

#ifndef ANSI_escape_h_
#define ANSI_escape_h_

#ifdef __cplusplus

#include <inttypes.h>
#include <string.h>
#include <Arduino.h>
#include <HardwareSerial.h>


// Uncomment this to enable some ansi processing tests on the device
// #define ANSI_TESTING


// Track the state of gathering the escape sequence
// - always begins ESC and ends with the first alpha character
// - parsing the contents of specific escape sequences is handled later
enum escStateEnum {
    escStateNone = 0,
    escStateEsc,
    escStateEnd
};

#define MAXESCLEN 30

#define APC_RX_NLCR_OFF    'a'
#define APC_RX_NLCR_ON     'A'
#define APC_RX_DELAYS_OFF  'b'
#define APC_RX_DELAYS_ON   'B'

#define IDENT_SEQUENCE  "\033[?1;0c"
#define SEQ_BINARY      "\033_ab\234"
#define SEQ_TEXT        "\033_AB\234"


class AnsiEscapeProcessor;


class AnsiEscapeProcessor
{
  public:
    AnsiEscapeProcessor();

    // Update with a single character.
    // The result is a length-prefixed buffer with zero or more characters to be
    // sent to the device.  (For example this might contain '\001' followed by `c`)
    uint8_t *update(uint8_t c);
    
    // The response (if any) to be sent back to the host, as a null-terminated string.
    uint8_t *getResponse();

    // Helpful getters
    int column();
    bool getIsWrapping() { return isWrapping; };
    bool getIsNLCR() { return isNLCR; };
    bool getIsNulDelays() { return isNulDelays; };
    bool getIsSoftReset() { bool b=isSoftReset; isSoftReset=false; return b; }
    bool getIsHardReset() { bool b=isHardReset; isHardReset=false; return b; }

  private:
    uint8_t outbuf[256];
    uint8_t retbuf[32];
    enum escStateEnum escState;

    // is this a 'zero-content' seqence (ESC followed by a single character?)
    bool isEscSimple;

    // Is this APC? ("ESC_...")
    bool isEscApc;

    // Is this CSI?  ("ESC[...")
    bool isEscCsi;

    // Is this CSI with questionmark?  ("ESC[?...")
    bool isCsiQuestion;

    // --- Processing state
    
    // Word wrapping?
    bool isWrapping;

    // NL -> CR+NL
    bool isNLCR;

    // insert NUL for delays after NL and CR
    bool isNulDelays;

    // Is the most recent escape instruction a reset code?
    bool isSoftReset;
    bool isHardReset;

    int col;
    uint8_t *pLen;
    uint8_t *pBuf;
    uint8_t nEscChars;
    uint8_t savedCol;
    uint8_t *pResponse;

    void init();
    bool isTerminator(uint8_t c);

    static bool isPrintable(uint8_t c) {
      return (c>=0x20 && c<=0x7E);
    }

    void writeOutput(const char *out, uint8_t n);
    void updateFromOutput();
    void updateFromChar(uint8_t c);

    void processSequence();
    int getN(int defaultN);
    void readAPC();
    void moveToColumn(int n);
    void setMode(int mode);
    void resetMode(int mode);
    void resetTerminal();

    void writeResponse(const char *out);
    void sendDA(int n);
    void sendDSR(int n);

};


/*
 * Implements the following:
 * 
 * CUD      ESC B       Cursor Down by 1
 * CUF      ESC C       Cursor Forward (Right) by 1
 * CUF      ESC [ Pn C  Cursor Forward (Right) by N
 * CUB      ESC D       Cursor Backward (Left) by 1
 * CUB      ESC [ Pn D  Cursor Backward (Left) by N
 * CHA      ESC [ Pn G  Cursor Horizontal Absolute - Move the active position to the n-th character of the active line.
 *
 * DECSC    ESC 7       save state (cursor position)
 * DECRC    ESC 8       restore saved state (cursor position)
 * 
 * DECAWM   ESC[? 7 h   Set AutoWrap Mode, start newline after column 72
 * DECAWM   ESC[? 7 l   Reset AutoWrap Mode, cursor remains at end of line after column 72
 *
 * DECSTR   ESC[!p      Soft Reset
 *
 * DA1      ESC[c       primary device attributes
 *          ESC[0c      primary device attributes
 *                      ESC [ ? 1; 0 c "I am a VT101 terminal with no options"
 * DSR      ESC[5n      device status report request
 *                      ESC 0 n - "I have no malfunction"
 * DSR      ESC[?15n    printer status request
 *                      ESC [? 13 n - "I have no printer"
 * CPR      ESC[6n      Cursor Position Report
 *                      ESC [ <row> ; <col> R
 * DECXCPR  ESC[?6n     Extended Cursor Position Report
 *                      ESC [ <row> ; <col>; <page> R
 *
 * APC      ESC _ <cmd> 0x9C (Application Program Command).
 *
 * APC commands are any number of bytes, each byte one of:
 *  APC_RX_NLCR        a (off), A (on) -- whether NL should insert a CR ("stty onlcr")
 *  APC_RX_DELAYS      b (off), B (on) -- whether to insert NUL as delay after NL/CR
 * Others except 0x9C are ignored, and specifically 0xC2 will always be ignored.
 * String Terminator is 0x9C or 0o234
 *
 *
 * (Not implemented; LATER MAYBE:)
 *
 * Tab stops (only because they're cool)
 * DECCAHT  ESC 2       clear all horizontal tabs
 * HTS      ESC H       horizontal tabulation set - sets a tab stop at the current column
 * DECHTS   ESC 1       horizontal tabulation set (LA34-specific)
 * TBC      ESC g       Clears a horizontal tab stop at cursor position
 * TBC      ESC 0 g     Clears a horizontal tab stop at cursor position
 * TBC      ESC 3 g     Clears all horizontal tab stops
 * DECSHTS  ESC[ Pn Pn u  set horizontal tabs (LA34-specific)
 * CHT      ESC[ Pn I   Cursor Horizontal Forward Tabulation - Move the active position n tabs forward. Default: 1.
 * CBT      ESC[ Pn Z   Cursor Backward Tabulation - Move the active position n tabs backward.  Default: 1.
 *
 * Auto-repeat (but there's a hardware repeat already, not much need for this)
 * DECARM   ESC[? 8 h   Selects auto repeat mode. A key pressed for more than 0.5 seconds automatically repeats.
 * DECARM   ESC[? 8 l   Turns off auto repeat. Keys pressed do not automatically repeat.
 *
 * DECRQM   report mode (eg. whether autowrap is set)
 *
 * RIS      ESC c       hard reset
 */


void test_ansi(usb_serial_class &serial);
void ansi_test(usb_serial_class &serial, const char *input, int expect_col, const char *expect_rsp);


#endif // __cplusplus
#endif // ANSI_escape_h_
