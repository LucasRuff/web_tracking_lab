#!/bin/bash
# Start the page server in the background
python page_server.py &
echo "Page server started on port 8080"

# Start the beacon server in the foreground
python beacon_server.py
