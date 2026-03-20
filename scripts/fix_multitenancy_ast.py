import os
import ast

base_dir = "/home/ubuntu/Projects/kuku-fiti-project/backend/app/api/v1"
files = [
    "alerts.py", "analytics.py", "audit.py", "biosecurity.py",
    "events.py", "finance.py", "flocks.py", "health.py",
    "inventory.py", "market.py", "people.py"
]

for filename in files:
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        continue

    with open(path, 'r') as f:
        content = f.read()
        lines = content.split("\n")

    if "set_tenant_context" not in content:
        import_line_idx = -1
        for idx, line in enumerate(lines):
            if "from app.api.deps import" in line:
                import_line_idx = idx
                break
        if import_line_idx != -1:
            line = lines[import_line_idx]
            if "set_tenant_context" not in line:
                lines[import_line_idx] = line.rstrip() + ", set_tenant_context"

    try:
        tree = ast.parse("\n".join(lines))
    except Exception as e:
        print(f"Failed to parse AST for {filename}: {e}")
        continue

    insertions = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            is_router = False
            for prev in node.decorator_list:
                if isinstance(prev, ast.Call) and isinstance(prev.func, ast.Attribute):
                    if prev.func.value.id == "router" and prev.func.attr in ['get', 'post', 'put', 'delete']:
                        is_router = True
            
            if is_router:
                has_db = any(arg.arg == "db" for arg in node.args.args) or any(arg.arg == "db" for arg in node.args.kwonlyargs)
                has_user = any(arg.arg == "current_user" for arg in node.args.args) or any(arg.arg == "current_user" for arg in node.args.kwonlyargs)

                if has_db and has_user:
                    if node.body:
                        first_node = node.body[0]
                        line_idx = first_node.lineno - 1
                        
                        orig_line = lines[line_idx]
                        indent = len(orig_line) - len(orig_line.lstrip())
                        indent_str = " " * indent
                        
                        insertions.append((line_idx, indent_str))

    # Remove duplicates if any
    insertions = list(set(insertions))
    insertions.sort(key=lambda x: x[0], reverse=True)
    
    for line_idx, indent_str in insertions:
        lines.insert(line_idx, f"{indent_str}await set_tenant_context(db, current_user)")

    with open(path, 'w') as f:
        f.write("\n".join(lines))
    print(f"Injected RLS into {filename}")

print("All RLS AST injections complete.")
