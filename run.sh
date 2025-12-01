#!/bin/bash
# Use venv Python if it exists (for local dev), otherwise use system Python (for Cloud Run)
if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
    .venv/bin/python main.py run
else
    python main.py run
fi

