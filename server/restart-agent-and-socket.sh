#!/usr/bin/env bash
clear

source ~/venvs/myenv/bin/activate
sleep 1

# -------------------------------------
echo "kill sockets"
kill -9 $(cat pid-sockets)
sleep 3

echo "kill agents"
kill -9 $(cat pid-agents)
sleep 3

echo "kill agents2"
agents2=$(ps -ef | grep spawn_main | grep -iv grep | awk '{print $2}')
kill -9 $agents2
sleep 1

# -------------------------------------
echo "start agents"
nohup uvicorn agent:app --reload --port 8082 > ./agents.log 2>&1 &
pidagents=$!
echo $pidagents
echo $pidagents > pid-agents
sleep 3

echo "start sockets"
python3 -u startall.py > sockets.log 2>&1 &
pidsockets=$!
echo $pidsockets
echo $pidsockets > pid-sockets
sleep 8


ss -tulpn
