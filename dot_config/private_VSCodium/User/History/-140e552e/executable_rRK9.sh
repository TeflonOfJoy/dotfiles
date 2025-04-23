#!/bin/bash

SCRIPT_PATH="/usr/bin/switch_to_2.sh"

while true; do
    # Get the cursor's current X position
    CURSOR_POSITION=$(kdotool getmouselocation --shell | grep x: | cut -d= -f2)
    
    # Get the screen width
    SCREEN_WIDTH=$(xdpyinfo | grep dimensions | awk '{print $2}' | cut -d'x' -f1)
    
    # Check if the cursor is at the right edge (X=max screen width)
    if [ "$CURSOR_POSITION" -ge "$((SCREEN_WIDTH - 1))" ]; then
        bash "$SCRIPT_PATH"
        sleep 2
    fi
    
    sleep 0.1
done