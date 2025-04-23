#!/bin/bash
ffplay -nodisp -fflags nobuffer -flags low_delay -strict experimental -fflags discardcorrupt -ar 48000 -analyzeduration 0 -probesize 32 -f s16le -i udp://0.0.0.0:18181?listen=1