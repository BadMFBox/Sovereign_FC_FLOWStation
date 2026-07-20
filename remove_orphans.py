#!/usr/bin/env python3

with open('FlowStation-v1.1.0-FC_FLOW.py', 'r') as f:
    lines = f.readlines()

# Find the line with "if __name__ == "__main__":"
main_block_line = None
for i, line in enumerate(lines):
    if line.strip() == 'if __name__ == "__main__":':
        main_block_line = i
        break

print(f"Main block at line {main_block_line + 1}")

# Keep everything up to and including main() + 1 line after it
# The structure should be:
# if __name__ == "__main__":
#     main()
# [EOF]

# Find where main() is called
main_call_line = None
for i in range(main_block_line, min(main_block_line + 5, len(lines))):
    if 'main()' in lines[i]:
        main_call_line = i
        break

print(f"main() call at line {main_call_line + 1}")

# Keep everything up to and including main() call
output = lines[:main_call_line + 1]

print(f"✅ Keeping {len(output)} lines, removing {len(lines) - len(output)} orphaned lines")

# Write back
with open('FlowStation-v1.1.0-FC_FLOW.py', 'w') as f:
    f.writelines(output)
