#!/usr/bin/env zsh
# Webcam status notifier for MSI Modern 15
# Run this script via KDE keyboard shortcut (XF86WebCam key)

# Allow time for hardware change to take effect
sleep 0.5

CAMERA_ON_ICON="/home/emanuel/Pictures/icons8-camera-48.png"
CAMERA_OFF_ICON="/home/emanuel/Pictures/icons8-no-camera-48.png"

# Check if any video devices exist
if ls /dev/video* &>/dev/null; then
    notify-send -a "Camera" -i "$CAMERA_ON_ICON" "Webcam Enabled" "Webcam is currently enabled"
else
    notify-send -a "Camera" -i "$CAMERA_OFF_ICON" "Webcam Disabled" "Webcam is currently disabled"
fi
