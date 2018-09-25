# Connecting with getty

To connect to OSX, I wanted the terminal to be a "real tty":  plug in and get the login prompt.

This is done using `getty`.  Follow the very detailed instructions here:
(Setting up a Serial Console in Mac OS X)[http://www.club.cc.cmu.edu/~mdille3/doc/mac_osx_serial_console.html]

I have this configured to auto-login as a specific OS user, and that user's `.profile` then sets up various
additional configuration items (stty, aliases, and so on).


