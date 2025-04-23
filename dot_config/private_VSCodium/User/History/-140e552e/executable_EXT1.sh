#!/bin/bash
SCRIPT_PATH="/usr/bin/switch_to_2.sh"

while true; do
    # Get the cursor's current X position
    # Note: Using grep to extract just the X value, then cut to get just the number
    CURSOR_POSITION=$(kdotool getmouselocation --shell | grep X= | cut -d= -f2)
    
    # Get the screen width
    SCREEN_WIDTH=1920  # Hardcoded since xdpyinfo seems to work correctly
    
    echo "Cursor position: $CURSOR_POSITION"
    echo "Screen width: $SCREEN_WIDTH"
    
    # Check if the cursor is at the right edge (X=max screen width)
    if [ -n "$CURSOR_POSITION" ] && [ "$CURSOR_POSITION" -ge "$((SCREEN_WIDTH - 1))" ]; then
        echo "Triggering script at right edge"
        sudo bash "$SCRIPT_PATH"
        sleep 2
    fi
    
    sleep 0.1
done