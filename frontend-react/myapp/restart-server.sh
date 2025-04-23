#!/bin/bash

clear
sudo kill -9 $(cat pid-www) > /dev/null 2>&1

 sudo nohup npm run dev --  --port 80 --host 0.0.0.0 > ./webserver.log 2>&1 &
#sudo nohup npm run dev > ./webserver.log 2>&1 &
echo $! > pid-www

sleep 5

ss -tulpn

