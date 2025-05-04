#!/usr/bin/env zsh

# Default config values
DEFAULT_EDGE="left"
DEFAULT_TOP_MARGIN=32
DEFAULT_LEFT_SCRIPT="$HOME/.local/bin/switch_to_1.sh"
DEFAULT_RIGHT_SCRIPT="$HOME/.local/bin/switch_to_2.sh"
DEFAULT_SCREEN_WIDTH=1920
DEFAULT_DEBOUNCE_COUNT=2
DEFAULT_MIN_MOVEMENT=50           # Minimum pixels cursor must move to reactivate detection

# Config file path
CONFIG_FILE="$HOME/.config/cursor_edge_switch.conf"

# Create default config file if it doesn't exist
if [ ! -f "$CONFIG_FILE" ]; then
    echo "# Cursor edge detection configuration" > "$CONFIG_FILE"
    echo "EDGE=$DEFAULT_EDGE                    # Options: left, right, both" >> "$CONFIG_FILE"
    echo "TOP_MARGIN=$DEFAULT_TOP_MARGIN        # Pixels from top to ignore on both edges" >> "$CONFIG_FILE"
    echo "LEFT_SCRIPT=$DEFAULT_LEFT_SCRIPT      # Script to run when left edge detected" >> "$CONFIG_FILE"
    echo "RIGHT_SCRIPT=$DEFAULT_RIGHT_SCRIPT    # Script to run when right edge detected" >> "$CONFIG_FILE"
    echo "SCREEN_WIDTH=$DEFAULT_SCREEN_WIDTH    # Screen width in pixels" >> "$CONFIG_FILE"
    echo "DEBOUNCE_COUNT=$DEFAULT_DEBOUNCE_COUNT # Number of detections before triggering" >> "$CONFIG_FILE"
    echo "MIN_MOVEMENT=$DEFAULT_MIN_MOVEMENT    # Pixels cursor must move to reactivate detection" >> "$CONFIG_FILE"
    echo "Created default config file at $CONFIG_FILE"
fi

# Load config file
source "$CONFIG_FILE"

# Set defaults for any missing values
EDGE=${EDGE:-$DEFAULT_EDGE}
TOP_MARGIN=${TOP_MARGIN:-$DEFAULT_TOP_MARGIN}
LEFT_SCRIPT=${LEFT_SCRIPT:-$DEFAULT_LEFT_SCRIPT}
RIGHT_SCRIPT=${RIGHT_SCRIPT:-$DEFAULT_RIGHT_SCRIPT}
SCREEN_WIDTH=${SCREEN_WIDTH:-$DEFAULT_SCREEN_WIDTH}
DEBOUNCE_COUNT=${DEBOUNCE_COUNT:-$DEFAULT_DEBOUNCE_COUNT}
MIN_MOVEMENT=${MIN_MOVEMENT:-$DEFAULT_MIN_MOVEMENT}

# Variables for tracking
left_consecutive_detections=0
right_consecutive_detections=0

# Variables to track cursor position at trigger time
left_trigger_x=0
left_trigger_y=0
right_trigger_x=0
right_trigger_y=0

# Edge active status
left_edge_active=true
right_edge_active=true

# Function to calculate distance between two points
calculate_distance() {
    local x1=$1
    local y1=$2
    local x2=$3
    local y2=$4
    
    # Simple Euclidean distance
    local x_diff=$((x2 - x1))
    local y_diff=$((y2 - y1))
    
    # We use the squared distance to avoid floating point
    local squared_dist=$((x_diff * x_diff + y_diff * y_diff))
    
    # Take square root to get actual distance (roughly)
    # We use bc for this calculation
    echo "sqrt($squared_dist)" | bc
}

# Exit handler for cleanup
cleanup() {
    echo "Script terminated. Cleaning up..."
    exit 0
}
trap cleanup SIGINT SIGTERM

echo "Starting cursor edge detection. Press Ctrl+C to exit."
echo "Monitoring edge(s): $EDGE"
echo "Top margin: $TOP_MARGIN pixels"
echo "Detection resumes after cursor moves $MIN_MOVEMENT pixels from edge"

while true; do
    # Get cursor position using more robust awk method
    CURSOR_INFO=$(kdotool getmouselocation --shell)
    CURSOR_X=$(echo "$CURSOR_INFO" | awk -F= '/X=/{print $2}')
    CURSOR_Y=$(echo "$CURSOR_INFO" | awk -F= '/Y=/{print $2}')
    
    # Check if cursor moved enough to reactivate left edge
    if ! $left_edge_active; then
        # Calculate distance moved since left edge trigger
        distance=$(calculate_distance "$left_trigger_x" "$left_trigger_y" "$CURSOR_X" "$CURSOR_Y")
        
        if [ "$distance" -ge "$MIN_MOVEMENT" ]; then
            echo "Left edge detection reactivated (cursor moved sufficient distance)"
            left_edge_active=true
        fi
    fi
    
    # Check if cursor moved enough to reactivate right edge
    if ! $right_edge_active; then
        # Calculate distance moved since right edge trigger
        distance=$(calculate_distance "$right_trigger_x" "$right_trigger_y" "$CURSOR_X" "$CURSOR_Y")
        
        if [ "$distance" -ge "$MIN_MOVEMENT" ]; then
            echo "Right edge detection reactivated (cursor moved sufficient distance)"
            right_edge_active=true
        fi
    fi

    # Check if cursor is below the top margin
    if [ "$CURSOR_Y" -gt "$TOP_MARGIN" ]; then
        # Check left edge if configured and active
        if [[ ("$EDGE" == "left" || "$EDGE" == "both") && "$left_edge_active" == true ]]; then
            if [ "$CURSOR_X" -le 0 ]; then
                left_consecutive_detections=$((left_consecutive_detections + 1))
                
                if [ "$left_consecutive_detections" -ge "$DEBOUNCE_COUNT" ]; then
                    echo "Cursor at left edge detected. Executing script..."
                    sudo "$LEFT_SCRIPT"
                    
                    # Store trigger position
                    left_trigger_x=$CURSOR_X
                    left_trigger_y=$CURSOR_Y
                    
                    # Deactivate left edge detection until cursor moves
                    left_edge_active=false
                    echo "Left edge detection paused until cursor moves $MIN_MOVEMENT pixels"
                    
                    # Reset left detection counter
                    left_consecutive_detections=0
                fi
            else
                left_consecutive_detections=0
            fi
        fi

        # Check right edge if configured and active
        if [[ ("$EDGE" == "right" || "$EDGE" == "both") && "$right_edge_active" == true ]]; then
            if [ "$CURSOR_X" -ge "$((SCREEN_WIDTH - 1))" ]; then
                right_consecutive_detections=$((right_consecutive_detections + 1))
                
                if [ "$right_consecutive_detections" -ge "$DEBOUNCE_COUNT" ]; then
                    echo "Cursor at right edge detected. Executing script..."
                    sudo "$RIGHT_SCRIPT"
                    
                    # Store trigger position
                    right_trigger_x=$CURSOR_X
                    right_trigger_y=$CURSOR_Y
                    
                    # Deactivate right edge detection until cursor moves
                    right_edge_active=false
                    echo "Right edge detection paused until cursor moves $MIN_MOVEMENT pixels"
                    
                    # Reset right detection counter
                    right_consecutive_detections=0
                fi
            else
                right_consecutive_detections=0
            fi
        fi
    else
        # Reset both counters if cursor is in the top margin
        left_consecutive_detections=0
        right_consecutive_detections=0
    fi

    sleep 0.1
done
