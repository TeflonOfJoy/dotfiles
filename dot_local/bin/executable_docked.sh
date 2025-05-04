#!/bin/bash

# Define the vendor and product ID of the Logi Bolt Receiver
VENDOR_ID="046d"
PRODUCT_ID="c548"

# Path to your scripts
TRANSMITTER_SCRIPT="$HOME/.local/bin/transmitter.sh"
CURSOR_EDGE_SWITCH_SCRIPT="$HOME/.local/bin/cursor_edge_switch.sh"

# Check if the Logi Bolt Receiver is connected
if lsusb | grep -q "$VENDOR_ID:$PRODUCT_ID"; then
    sleep 10
    # Start each script in a separate Konsole tab using zsh explicitly
    konsole --tabs-from-file ./ktabs --background-mode &
fi
