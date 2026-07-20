#!/usr/bin/env python3

with open('FlowStation-v1.1.0-FC_FLOW.py', 'r') as f:
    lines = f.readlines()

# Find do_POST method
do_post_line = None
for i, line in enumerate(lines):
    if 'def do_POST(self):' in line:
        do_post_line = i
        break

print(f"Found do_POST at line {do_post_line + 1}")

# Find where to insert (after the first if/elif)
insert_line = None
for i in range(do_post_line + 1, do_post_line + 20):
    if 'elif self.path' in lines[i] or 'if self.path' in lines[i]:
        insert_line = i + 1
        break

if insert_line:
    # Insert the route
    route_code = '''            elif self.path.startswith('/api/ai-notes-write/'):
                self._handle_ai_notes_write()
'''
    lines.insert(insert_line, route_code)
    
    with open('FlowStation-v1.1.0-FC_FLOW.py', 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Added route at line {insert_line + 1}")
else:
    print("❌ Could not find insertion point")
