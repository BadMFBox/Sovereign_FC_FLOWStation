#!/usr/bin/env python3
import os

# Get the directory where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def read_file(filename):
    """Read file from the same directory as this script"""
    path = os.path.join(SCRIPT_DIR, filename)
    with open(path) as f:
        return f.read()

# Read all room files
room1 = read_file("room1_command_post.html")
room2 = read_file("room2_file_status.html")
room3 = read_file("room3_terminal.html")
room4 = read_file("room4_ai_chat.html")
layout = read_file("main_layout.html")

# Try to read connector and client JS
try:
    connector_js = read_file("flowstation_connector.js")
except:
    connector_js = ""

try:
    client_js = read_file("client_v2.js")
except:
    try:
        client_js = read_file("client.js")
    except:
        client_js = ""

# Replace placeholders
layout = layout.replace('ROOM1_CONTENT', room1)
layout = layout.replace('ROOM2_CONTENT', room2)
layout = layout.replace('ROOM3_CONTENT', room3)
layout = layout.replace('ROOM4_CONTENT', room4)

# Inline JavaScript
if connector_js:
    js_combined = connector_js + '\n\n' + client_js
else:
    js_combined = client_js

layout = layout.replace('<script src="rooms/client.js"></script>', f'<script>{js_combined}</script>')

print(layout)
