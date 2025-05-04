#!/usr/bin/env zsh

ffmpeg -f pulse -i "remote.monitor" \
       -acodec pcm_s16le -ar 48000 -ac 2 \
       -f s16le \
       -flush_packets 1 \
       -fflags nobuffer \
       -max_delay 100000 \  # 100ms max delay
       -packetsize 512 \
       "udp://192.168.1.37:18181?pkt_size=512&buffer_size=2097152"
