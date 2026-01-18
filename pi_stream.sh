#!/bin/bash

# USEFUL COMMANDS
# v4l2-ctl --list-devices
# sudo ldconfig && rpicam-hello --list-cameras
# https://medium.com/@sepideh.92sh/setup-and-troubleshooting-of-raspberry-pi-camera-module-v2-1-imx219-on-ubuntu-24-04-lts-fb518f4576c0

LAPTOP_IP="192.168.6.1"

# CSI Camera 1
rpicam-vid --camera 0 -t 0 --width 640 --height 480 --framerate 30 \
  --codec mjpeg --quality 70 -n -o - | \
  gst-launch-1.0 fdsrc ! jpegparse ! rtpjpegpay ! \
  udpsink host=$LAPTOP_IP port=5000 &

# CSI Camera 2
rpicam-vid --camera 1 -t 0 --width 640 --height 480 --framerate 30 \
  --codec mjpeg --quality 70 -n -o - | \
  gst-launch-1.0 fdsrc ! jpegparse ! rtpjpegpay ! \
  udpsink host=$LAPTOP_IP port=5002 &

# USB Camera 3 (Change /dev/video0 if needed)
gst-launch-1.0 v4l2src device=/dev/video16 ! \
    video/x-raw,width=640,height=480 ! \
    videoconvert ! jpegenc quality=70 ! rtpjpegpay ! udpsink host=$LAPTOP_IP port=5004 &

wait
