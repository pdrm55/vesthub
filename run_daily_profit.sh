#!/bin/bash

# ==========================================
# VestHub Profit Distribution Cron Script
# ==========================================

# 1. Define Paths (Adjust if your production path differs)
PROJECT_DIR="/Users/pedrammotlagh/Projects/VestHub/vesthub"
LOG_FILE="$PROJECT_DIR/logs/cron_profit.log"
VENV_ACTIVATE="$PROJECT_DIR/venv/bin/activate"

# 2. Navigate to Project Directory
cd "$PROJECT_DIR" || { echo "Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }

# 3. Activate Virtual Environment
source "$VENV_ACTIVATE"

# 4. Set Flask App
export FLASK_APP=app.py

# 5. Run Command & Append to Log
echo "[$(date)] Starting Profit Recovery..." >> "$LOG_FILE"
flask recover-profits >> "$LOG_FILE" 2>&1
echo "[$(date)] Finished." >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"