#!/usr/bin/env zsh

# Switch MX Keys S to channel 1
hidapitester --vidpid 046D:C548 --usage 0x0001 --usagePage 0xFF00 --open --length 7 --send-output 0x10,0x02,0x0a,0x1c,0x00,0x00,0x00

# Switch MX Master 3S to channel 1
hidapitester --vidpid 046D:C548 --usage 0x0001 --usagePage 0xFF00 --open --length 7 --send-output 0x10,0x01,0x0a,0x1d,0x00,0x00,0x00
