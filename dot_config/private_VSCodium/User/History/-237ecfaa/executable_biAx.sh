#!/bin/bash
# Create a null sink to receive audio
pactl load-module module-null-sink sink_name=network_in sink_properties=device.description="Network Audio In"

# Receive and play audio
ffmpeg -fflags nobuffer -flags low_delay -strict experimental -f s16le -ar 48000 -i udp://0.0.0.0:18181?listen=1 -f pulse network_in