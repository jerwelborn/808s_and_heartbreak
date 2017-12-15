#!/bin/bash


# update sensor 
echo -e "\nBurning code to sensor boards...\n"
make -f sensor-board.make && \
make -f sensor-board.make program-usbtiny && \
# update rpi
echo -e "\nscp-ing script to raspberry pi...\n"
./update-rpi.sh  