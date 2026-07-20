#!/usr/bin/env python3

with open('FlowStation-v1.1.0-FC_FLOW.py', 'r') as f:
    lines = f.readlines()

# Find the if __name__ block
if_name_line = None
for i, line in enumerate(lines):
    if 'if __name__ == "__main__":' in line:
        if_name_line = i
        break

print(f"if __name__ at line {if_name_line + 1}")

# Find main() call (should be 1-2 lines after)
main_call_line = None
for i in range(if_name_line, min(if_name_line + 10, len(lines))):
    if 'main()' in lines[i] and 'def main' not in lines[i]:
        main_call_line = i
        break

print(f"main() call at line {main_call_line + 1}")

# Everything after main() call is orphaned duplicates
# Keep everything UP TO AND INCLUDING the main() call line
output = lines[:main_call_line + 1]

print(f"Original: {len(lines)} lines")
print(f"Keeping: {len(output)} lines")
print(f"Removing: {len(lines) - len(output)} orphaned lines")

with open('FlowStation-v1.1.0-FC_FLOW.py', 'w') as f:
    f.writelines(output)

print("✅ Removed orphaned duplicates")
