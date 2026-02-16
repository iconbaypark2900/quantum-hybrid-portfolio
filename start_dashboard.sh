#!/bin/bash
# Script to start the Quantum Hybrid Portfolio Dashboard

echo "Starting Quantum Hybrid Portfolio Dashboard..."
echo "Access the dashboard at: http://localhost:8050"
echo "Press Ctrl+C to stop the server."

cd "$(dirname "$0")"
source .venv/bin/activate
python dashboard.py