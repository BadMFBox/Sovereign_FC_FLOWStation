#!/usr/bin/env python3

with open('FlowStation-v1.1.0-FC_FLOW.py', 'r') as f:
    lines = f.readlines()

# Find all do_POST locations
do_post_lines = []
for i, line in enumerate(lines):
    if '    def do_POST(self):' in line:
        do_post_lines.append(i)

print(f"Found do_POST at lines: {[x+1 for x in do_post_lines]}")

# Strategy: Remove only lines 2130-2241 and 2242-2353 (the duplicate do_POST methods)
# Keep everything else including the AI handler methods

output = []
skip_ranges = [
    (2129, 2241),  # Second do_POST block
    (2241, 2353)   # Third do_POST block
]

for i, line in enumerate(lines):
    # Check if we're in a skip range
    in_skip_range = False
    for start, end in skip_ranges:
        if start <= i < end:
            in_skip_range = True
            break
    
    if not in_skip_range:
        output.append(line)

print(f"✅ Keeping {len(output)} lines, removing {len(lines) - len(output)}")

# Write back
with open('FlowStation-v1.1.0-FC_FLOW.py', 'w') as f:
    f.writelines(output)
