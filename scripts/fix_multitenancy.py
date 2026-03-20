import os
import re

base_dir = "/home/ubuntu/Projects/kuku-fiti-project/backend/app/api/v1"

files = [
    "alerts.py", "analytics.py", "audit.py", "biosecurity.py",
    "events.py", "finance.py", "flocks.py", "health.py",
    "inventory.py", "market.py", "people.py"
]

injection = "    await set_tenant_context(db, current_user)\n"

for filename in files:
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        print(f"Skipping {filename} (not found)")
        continue

    with open(path, 'r') as f:
        content = f.read()

    # 1. Ensure set_tenant_context is imported
    if "set_tenant_context" not in content:
        # Match 'from app.api.deps import ...'
        # e.g. from app.api.deps import get_db, get_current_user
        match = re.search(r'from app\.api\.deps import ([^\n]+)', content)
        if match:
            imports = match.group(1).strip()
            if "set_tenant_context" not in imports:
                new_imports = imports + ", set_tenant_context"
                content = content.replace(match.group(0), f"from app.api.deps import {new_imports}")
    
    # 2. Find route handlers with async def and both db and current_user
    # Regex explanation:
    # async def [name]([args]):
    # \s*"""[docstring]"""
    pattern = r'async def [a-zA-Z_0-9]+\([^)]*db:\s*AsyncSession[^)]*current_user[^)]*\):(\s*"""[^"]+""")?'
    
    def replacer(match):
        orig = match.group(0)
        # Check if set_tenant_context already called (prevent duplicates)
        # However, checking entire function body is hard with just signature match.
        # So we look at the lines immediately FOLLOWING the match to see if it's there.
        return orig + "\n" + injection

    # To do it safely, let's just find and split on the function signature.
    # It might be easier to parse Line by Line for '@router.' and 'async def'
    
    new_content = ""
    lines = content.split("\n")
    i = 0
    while i < len(lines):
        new_content += lines[i] + "\n"
        if lines[i].startswith("@router."):
            # We are entering a route handler definition
            # Find the async def line
            j = i + 1
            is_route = False
            while j < len(lines) and not lines[j].startswith("async def"):
                # Inside decorators, skip
                if lines[j].startswith("@"): j += 1; continue
                j += 1
            if j < len(lines) and lines[j].startswith("async def"):
                # Found function signature, now consume until we find ':'
                # Multiple line signatures might happen
                sig_lines = []
                k = j
                while k < len(lines) and "):" not in lines[k]:
                    sig_lines.append(lines[k])
                    k += 1
                if k < len(lines):
                    sig_lines.append(lines[k]) # Add the last one
                
                sig = " ".join(sig_lines)
                if "db:" in sig and "current_user" in sig:
                    is_route = True
                    
                if is_route:
                    # Advance i to k (skip signature adding)
                    # We need to just write sig_lines back
                    sig_index = j
                    while sig_index <= k and sig_index < len(lines):
                         new_content += lines[sig_index] + "\n"
                         sig_index += 1
                    i = k # advanced i to bottom of sig
                    
                    if i >= len(lines):
                         break
                    
                    # Next line could be docstring
                    if i + 1 < len(lines) and '"""' in lines[i+1]:
                         new_content += lines[i+1] + "\n"
                         if lines[i+1].strip().endswith('"""') and len(lines[i+1].strip()) > 3:
                             # single line doc
                             new_content += injection
                             i += 1
                         else:
                             # multi-line doc
                             i += 1
                             while i < len(lines) and '"""' not in lines[i+1]:
                                  i += 1
                                  new_content += lines[i] + "\n"
                             if i + 1 < len(lines):
                                  i += 1
                                  new_content += lines[i] + "\n"
                             new_content += injection
                    else:
                         new_content += injection
                    i += 1
                    continue
                        
            # if not route or not matched correctly, fallback
        i += 1

    with open(path, 'w') as f:
        f.write(new_content.rstrip("\n") + "\n")
    print(f"Processed {filename}")

print("All RLS injections processed.")
