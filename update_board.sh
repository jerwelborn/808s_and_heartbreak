#!/bin/bash

# update sensor 
echo -e "\nBurning code to sensor boards...\n"
make -f sensor_board.make && \
make -f sensor_board.make program-usbtiny
