#!/usr/bin/env python

# print all the printable characters

import sys

for c in range(0x20, 0x60):
  print(chr(c) * 10)

