
import os
import re

# Configuration
base_dir = "/Users/maxlanies/Git/2GC/cloudbridge-relay-installer/oss-repositories/cloudbridge-docs/ARCHITECTURE"

file_map = {
    "PROJECT_OVERVIEW.md": "OVERVIEW",
    "COMPLETE_ARCHITECTURE_GUIDE.md": "OVERVIEW",
    "ARCHITECTURE_FLOW.md": "CORE",
    "PROTOCOL_STACK.md": "CORE",
    "NETWORK_LAYERS_OSI_MODEL.md": "CORE",
    "CLIENT_ARCHITECTURE.md": "COMPONENTS",
    "DNS_NETWORK_ARCHITECTURE.md": "COMPONENTS",
    "TENANT_ISOLATION_ARCHITECTURE.md": "COMPONENTS",
    "DATA_SOURCES.md": "REFERENCE",
    "REQUIREMENTS_MATRIX.md": "REFERENCE",
    "REQUIREMENTS_MATRIX_GUIDE.md": "REFERENCE",
    "START_HERE.md": "ROOT",
    "INDEX.md": "ROOT",
    "README.md": "ROOT"
}

subdirs = ["OVERVIEW", "CORE", "COMPONENTS", "REFERENCE"]

def get_relative_path(source_folder, target_file):
    target_folder = file_map.get(target_file)
    if not target_folder:
        return None # File not tracked
    
    if source_folder == target_folder:
        return target_file
    
    if target_folder == "ROOT":
        return f"../{target_file}"
        
    return f"../{target_folder}/{target_file}"

def process_file(filepath, folder_name):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return
    
    new_content = content
    
    for filename in file_map.keys():
        replacement = get_relative_path(folder_name, filename)
        if replacement and replacement != filename:
            # Replace (filename) with (replacement)
            # We use a pattern that avoids double replacement if possible, 
            # but simple replacement is robust enough if we assume filenames are unique enough
            # and we are not running this multiple times on same file (idempotency issues with simple replace).
            # To be safer, we look for `](filename)` 
            
            new_content = new_content.replace(f"]({filename})", f"]({replacement})")
            
    if new_content != content:
        print(f"Updating {filepath}")
        with open(filepath, 'w') as f:
            f.write(new_content)

def main():
    print("Starting link update...")
    for folder in subdirs:
        folder_path = os.path.join(base_dir, folder)
        if not os.path.exists(folder_path):
            continue
        
        for filename in os.listdir(folder_path):
            if filename.endswith(".md"):
                process_file(os.path.join(folder_path, filename), folder)
    print("Done.")

if __name__ == "__main__":
    main()
