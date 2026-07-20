#!/usr/bin/env python3

with open('FlowStation-v1.1.0-FC_FLOW.py', 'r') as f:
    lines = f.readlines()

# Find where build_html starts (this is where MeshHTTPHandler ends)
build_html_idx = None
for i, line in enumerate(lines):
    if line.startswith('def build_html'):
        build_html_idx = i
        break

# Find where AI methods are now (around line 2354)
ai_methods_start = None
for i, line in enumerate(lines):
    if '    def _handle_ai_chat(self):' in line:
        ai_methods_start = i
        break

print(f"MeshHTTPHandler ends at line {build_html_idx} (build_html starts)")
print(f"AI methods currently at line {ai_methods_start + 1}")

# Find where AI methods end (before def main or if __name__)
ai_methods_end = None
for i in range(ai_methods_start + 1, len(lines)):
    if lines[i].startswith('def ') or lines[i].startswith('if __name__'):
        ai_methods_end = i
        break

# Extract AI methods
ai_methods = lines[ai_methods_start:ai_methods_end]
print(f"Extracting {len(ai_methods)} lines of AI methods")

# Build new file:
# 1. Everything up to build_html (includes MeshHTTPHandler)
# 2. AI methods (insert here, INSIDE the class)
# 3. build_html onwards (but skip the old AI methods section)

output = []
output.extend(lines[:build_html_idx])           # Up to build_html
output.extend(ai_methods)                        # AI methods
output.append('\n')
output.extend(lines[build_html_idx:ai_methods_start])  # build_html to where AI methods were
output.extend(lines[ai_methods_end:])           # After AI methods to end

print(f"New file: {len(output)} lines (was {len(lines)})")

with open('FlowStation-v1.1.0-FC_FLOW.py', 'w') as f:
    f.writelines(output)

print("✅ Moved AI methods inside MeshHTTPHandler class")
