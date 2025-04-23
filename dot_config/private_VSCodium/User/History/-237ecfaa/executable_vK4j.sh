ffplay -nodisp -flags low_delay -avioflags direct \
       -fflags nobuffer+discardcorrupt -strict experimental \
       -analyzeduration 0 -probesize 32 \
       -f s16le -ch_layout stereo -sample_rate 48000 \
       -i "udp://0.0.0.0:18181?listen=1&buffer_size=65536"