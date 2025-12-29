import os

# Configuration
ROOT_DIR = r"c:\Users\User\.gemini\antigravity\playground\celestial-shuttle"
OUTPUT_DIR = r"c:\Users\User\.gemini\antigravity\brain\0dae1a15-9369-4ca6-9ffe-1456db7098e0"
MAX_LINES_PER_FILE = 10000000 # Single file

# Extensions to include
EXTENSIONS = {
    '.py', '.tsx', '.ts', '.js', '.jsx', '.css', '.html', 
    '.json', '.md', '.sql', '.yaml', '.yml', '.env.example'
}

# Directories/Files to ignore
IGNORE_DIRS = {
    'node_modules', '__pycache__', '.git', '.idea', '.vscode', 
    'dist', 'build', 'coverage', 'venv', 'env', '.mypy_cache',
    'migrations', # Optional: skip auto-generated migrations if too many
    'assets' # Binary assets
}
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock'
}

def is_ignored(path, names):
    return set(names).intersection(IGNORE_DIRS)

def collect_files(root_dir):
    all_files = []
    for root, dirs, files in os.walk(root_dir):
        # Filter directories inplace
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file in IGNORE_FILES:
                continue
                
            ext = os.path.splitext(file)[1]
            if ext in EXTENSIONS:
                all_files.append(os.path.join(root, file))
    return all_files

def main():
    files = collect_files(ROOT_DIR)
    print(f"Found {len(files)} files.")
    
    current_part = 1
    current_lines = 0
    current_content = []
    
    def save_chunk():
        if not current_content:
            return
        filename = f"project_full.txt"
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("".join(current_content))
        print(f"Saved {path} ({current_lines} lines)")

    for file_path in files:
        try:
            rel_path = os.path.relpath(file_path, ROOT_DIR)
            
            # Simple header
            header = f"\n{'='*50}\nFILE: {rel_path}\n{'='*50}\n"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            file_lines = content.count('\n') + header.count('\n') + 2
            
            # Check if we need to rotate
            if current_lines + file_lines > MAX_LINES_PER_FILE:
                save_chunk()
                current_part += 1
                current_lines = 0
                current_content = []
            
            current_content.append(header)
            current_content.append(content)
            current_content.append("\n")
            current_lines += file_lines
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    # Save last chunk
    save_chunk()
    print("Export complete.")

if __name__ == "__main__":
    main()
