import os

def refactor_imports():
    root_dir = "backend"
    target = "app.infrastructure"
    replacement = "infrastructure"
    
    count = 0
    for subdir, dirs, files in os.walk(root_dir):
        if "node_modules" in subdir or ".git" in subdir or "__pycache__" in subdir:
            continue
            
        for file in files:
            if not file.endswith(".py"):
                continue
                
            filepath = os.path.join(subdir, file)
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            if target in content:
                new_content = content.replace(target, replacement)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated: {filepath}")
                count += 1
                
    print(f"Total files updated: {count}")

if __name__ == "__main__":
    refactor_imports()
