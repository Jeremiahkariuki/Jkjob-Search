#!/usr/bin/env bash
# Script to install daily cron job for EMEA Remote Tech Job Intelligence System
# Runs every day at 08:00 AM East Africa Time (Africa/Nairobi - UTC+3)

PROJECT_DIR="/Users/Jeremy/Documents/antigravity/adventurous-bardeen"
PYTHON_BIN="/usr/local/bin/python3"
CRON_CMD="0 8 * * * cd $PROJECT_DIR && $PYTHON_BIN run.py >> reports/cron_execution.log 2>&1"

echo "=========================================================="
echo "Configuring Daily Automation for EMEA Job Intelligence"
echo "Target Schedule: Daily at 08:00 AM EAT (Africa/Nairobi)"
echo "Project Directory: $PROJECT_DIR"
echo "=========================================================="

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -F "$PROJECT_DIR") >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "[!] Cron job already exists in your crontab."
else
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "[✓] Daily cron job registered successfully!"
fi

echo ""
echo "Current crontab entries:"
crontab -l | grep "$PROJECT_DIR"
echo "=========================================================="
