#!/usr/bin/env python3

with open('FlowStation-v1.1.0-FC_FLOW.py', 'r') as f:
    lines = f.readlines()

# Find main() function
main_idx = None
for i, line in enumerate(lines):
    if line.strip() == 'def main():':
        main_idx = i
        break

# Find where AI methods start (after main)
ai_start = None
for i in range(main_idx + 1, len(lines)):
    if '    def _handle_ai_chat(self):' in lines[i]:
        ai_start = i
        break

print(f"main() at {main_idx + 1}")
print(f"AI methods start at {ai_start + 1}")

# Find where AI methods end (at EOF)
ai_end = len(lines)

# Extract AI methods
ai_methods = lines[ai_start:ai_end]
print(f"Extracting {len(ai_methods)} lines of AI methods")

# Remove AI methods from their current location
new_lines = lines[:ai_start]

# Insert AI methods BEFORE main() with proper indentation
# Insert at main_idx position
output = lines[:main_idx] + ai_methods + ['\n'] + lines[main_idx:ai_start]

print(f"New file will have {len(output)} lines")

with open('FlowStation-v1.1.0-FC_FLOW.py', 'w') as f:
    f.writelines(output)

print("✅ Moved AI methods before main()")
