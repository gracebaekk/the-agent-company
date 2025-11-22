#!/bin/bash
# Use venv Python if it exists, otherwise use system Python
if [ -d ".venv" ]; then
    .venv/bin/python main.py run
else
    python main.py run
fi

