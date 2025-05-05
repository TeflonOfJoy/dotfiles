#!/usr/bin/env zsh

# Define the IP address to ping
TARGET_IP="192.168.1.100"  # Replace with your target device's IP

# Path to your scripts
TRANSMITTER_SCRIPT="$HOME/.local/bin/receiver.sh"
CURSOR_EDGE_SWITCH_SCRIPT="$HOME/.local/bin/cursor_edge_switch.sh"

# Check if the target IP is reachable via ping
if ping -c 1 -W 2 $TARGET_IP &> /dev/null; then
    echo "Device at $TARGET_IP is connected to the network"
    sleep 10
    # Start each script in a separate Konsole tab using zsh explicitly
    konsole --tabs-from-file $HOME/.config/ktabs --background-mode &
else
    echo "Device at $TARGET_IP is not connected to the network"
fi
