ffplay -nodisp -flags low_delay -avioflags direct \
       -fflags nobuffer+discardcorrupt -strict experimental \
       -analyzeduration 0 -probesize 32 \
       -f s16le -ar 48000 -ac 2 \
       -i "udp://0.0.0.0:18181?listen=1&buffer_size=1024"