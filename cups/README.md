# Installing a "printer driver"

The teletype is four devices in one: hardcopy display (printer), tape punch, keyboard, and tape reader.  So, shouldn't the printer be available to modern applications?

Here's how to configure a Raspberry Pi to share the teletype as a networked printer, using CUPS.

## TODO

Still to do:
* Correct conversion to ASCII-63 (it's not utf-8).
* Application-aware flow control.  Print jobs should queue in background if the terminal is being used interactively.  When the interactive user is idle, they can print again.
(This is also the general queueing method that I want for other purposes, such as for automatic printing of news, twitter, and other messages).
* Document formats other than text/plain.  CUPS will convert filetypes, e.g. from postscript and pdf, but we must prevent them from going through
rasterization (to preserve the original text).
* Somehow enable *bold* text formatting by overstriking each letter.


## Installing CUPS

Make sure the basic packages are up-to-date,
```
sudo apt-get update && sudo apt-get upgrade
```

Install CUPS and also the IPP utilities (ippfind, ipptool),
```
sudo apt-get install cups cups-ipp-utils
sudo cupsctl --remote-any --share-printers
sudo /etc/init.d/cups restart
```

When the CUPS web UI is enabled, you can navigate to it with a browser, and log in using unix credentials.  (You may need to add the 'pi' user to the lpadmin group for this).
```
https://pi:631/admin
```

## Installing the print driver

Copy the teletype driver file [tty.drv](tty.drv) to
```
    /usr/share/cups/drv/
```

Copy the [teletype.png](teletype.png) image to
```
    /var/cache/cups/teletype.png
```

Create the printer.  Assuming that the teletype is connected as the `/dev/ttyACM0' serial device, 
```
lpadmin -p teletype -E -v serial:/dev/ttyACM0 -m drv:///tty.drv/tty.ppd -o cupsIPPSupplies=true -L "upstairs" -D "Teletype printer"
```

Then you can print locally,
```
echo "hi" | lp -d teletype
```
and the printer should also be discoverable on the network.

## Customizing the CUPS filters

(TODO)

