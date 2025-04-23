#!/usr/bin/env bash

#!/bin/bash

clear
uvicorn agent:app --reload --port 8082 > ./agents.log 2>&1 &
pid=$!
echo $pid
echo $pid > pid-agents

