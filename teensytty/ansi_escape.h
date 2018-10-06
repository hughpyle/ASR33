

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


class AnsiEscapeProcessor;


class AnsiEscapeProcessor
{
  public:
    AnsiEscapeProcessor();

    // Update with a single character.
    // The result is a length-prefixed buffer with zero or more characters to be
    // sent to the device.  (For example this might contain '\001' followed by `c`)
    uint8_t *update(uint8_t c);
    
    // The response (if any) to be sent back to the host.
    // (not yet implemented)
    // uint8_t *getResponse();

    // Helpful getter
    int column();

  private:
    uint8_t outbuf[256];
    enum escStateEnum escState;

    // is this a 'zero-content' seqence (ESC followed by a single character?)
    // If not, we only handle CSI sequences ("ESC[...")
    bool isEscSimple;

    // Is this CSI with questionmark?  ("ESC[?...")
    bool isEscCsi;
    bool isCsiQuestion;

    // Word wrapping?
    bool isWrapping;

    int col;
    uint8_t *pLen;
    uint8_t *pBuf;
    uint8_t nEscChars;
    uint8_t savedCol;

    bool isTerminator(uint8_t c);

    static bool isPrintable(uint8_t c) {
      return (c>=0x20 && c<=0x7E);
    }

    void writeOutput(const char *out, uint8_t n);
    void updateFromOutput();
    void updateFromChar(uint8_t c);

    void processSequence();
    int getN(int defaultN);
    // int getX(int defaultY);
    // int getY(int defaultX);
    void moveToColumn(int n);
    void setMode(int mode);
    void resetMode(int mode);
    void resetTerminal();
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
 * (Not implemented; LATER MAYBE:)
 * 
 * Tab stops:
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
 * DECARM   ESC[? 8 h   Selects auto repeat mode. A key pressed for more than 0.5 seconds automatically repeats.
 * DECARM   ESC[? 8 l   Turns off auto repeat. Keys pressed do not automatically repeat.
 *
 * DA       ESC[c or ESC[0c - respond with terminal info
 *             ESC [ ? 1; 0 c "I am a VT101 terminal with no options"
 * DSR      ESC 5 n - device status report request
 *             ESC 0 n - "I have no malfunction"
 * DSR      ESC ? 15 n - printer status request
 *             ESC ? 13 n - "I have no printer"
 *             
 * RIS      ESC c       hard reset
 */


void test_ansi(usb_serial_class &serial);
void ansi_test(usb_serial_class &serial, const char *input, int expect_col);


#endif // __cplusplus
#endif // ANSI_escape_h_
