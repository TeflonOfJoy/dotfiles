#!/bin/bash
# Receive and play audio to default output
ffmpeg -f s16le -ar 48000 -i udp://0.0.0.0:18181?listen=1 -f pulse default