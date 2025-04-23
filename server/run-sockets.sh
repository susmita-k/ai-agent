#!/usr/bin/env bash

#!/bin/bash

clear
python3 startall.py > sockets.log 2>&1 &
pid=$!
echo $pid
echo $pid > pid-sockets
