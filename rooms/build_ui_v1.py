import os

# Read components
def read_file(path):
    with open(path) as f:
        return f.read()

room1 = read_file("rooms/room1_command_post.html")
room2 = read_file("rooms/room2_file_status.html")
room3 = read_file("rooms/room3_terminal.html")
room4 = read_file("rooms/room4_ai_chat.html")
connector_js = read_file("rooms/flowstation_connector.js")
client_js = read_file("rooms/client_v2.js")
layout = read_file("rooms/main_layout.html")

# Replace placeholders
layout = layout.replace('ROOM1_CONTENT', room1)
layout = layout.replace('ROOM2_CONTENT', room2)
layout = layout.replace('ROOM3_CONTENT', room3)
layout = layout.replace('ROOM4_CONTENT', room4)

# Inline JavaScript (connector first, then client)
js_combined = connector_js + '\n\n' + client_js
layout = layout.replace('<script src="rooms/client.js"></script>', f'<script>{js_combined}</script>')

print(layout)
