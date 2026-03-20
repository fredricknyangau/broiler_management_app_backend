import os

base_dir = "/home/ubuntu/Projects/kuku-fiti-project/backend/app/api/v1"

files = [
    "alerts.py", "analytics.py", "audit.py", "biosecurity.py",
    "events.py", "finance.py", "flocks.py", "health.py",
    "inventory.py", "market.py", "people.py"
]

target = "    await set_tenant_context(db, current_user)\n    await set_tenant_context(db, current_user)\n"
sub = "    await set_tenant_context(db, current_user)\n"

for filename in files:
    path = os.path.join(base_dir, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            content = f.read()
        
        if target in content:
            content = content.replace(target, sub)
            with open(path, 'w') as f:
                f.write(content)
            print(f"Cleaned duplicates in {filename}")

print("Cleanup complete.")
