import os

# Configuration
ROOT_DIR = "."
OUTPUT_FILE = "codebase_dump.md"

INCLUDE_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.json', 
    '.css', '.html', '.ini', '.yaml', '.yml', 
    '.txt', '.md', '.dockerfile'
}

EXCLUDE_DIRS = {
    'node_modules', 'venv', '.git', '__pycache__', 
    'dist', 'build', '.idea', '.vscode', '.pytest_cache',
    'backend copy', 'brain'
}

EXCLUDE_FILES = {
    'package-lock.json', 'yarn.lock', '.ds_store', 
    'codebase_dump.md', 'collect_codebase.py',
    '.env'
}

def get_md_lang(ext):
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
        '.css': 'css',
        '.html': 'html',
        '.md': 'markdown'
    }
    return mapping.get(ext, '')

def is_source_file(filename):
    name_lower = filename.lower()
    if name_lower in EXCLUDE_FILES: return False
    if name_lower == '.env' or (name_lower.startswith('.env') and 'example' not in name_lower): return False
    _, ext = os.path.splitext(name_lower)
    if ext in INCLUDE_EXTENSIONS: return True
    if name_lower == 'dockerfile': return True
    return False

def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        outfile.write("# VoiceBrain Project Codebase Dump\n\n")
        outfile.write(f"Generated on: {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}\n\n")
        
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and d.lower() not in EXCLUDE_DIRS]
            files.sort()
            
            for filename in files:
                if is_source_file(filename):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, ROOT_DIR).replace("\\", "/")
                    _, ext = os.path.splitext(filename.lower())
                    lang = get_md_lang(ext)
                    
                    try:
                        with open(filepath, "r", encoding="utf-8", errors='replace') as infile:
                            content = infile.read()
                        
                        outfile.write(f"## File: `{rel_path}`\n\n")
                        outfile.write(f"```{lang}\n")
                        outfile.write(content)
                        if not content.endswith('\n'): outfile.write('\n')
                        outfile.write("```\n\n---\n\n")
                        print(f"Added: {rel_path}")
                    except Exception as e:
                        print(f"Error reading {filepath}: {e}")

    print(f"\nDone. Codebase exported to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
