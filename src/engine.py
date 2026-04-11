import hashlib
import os

def generate_manifest(file_path: str, block_size: int):
    manifest = {}
    
    if not os.path.exists(file_path):
        return manifest

    with open(file_path, 'rb') as f:
        block_index = 0
        
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            
            hashed = hashlib.sha256(chunk).hexdigest()
            manifest[block_index] = hashed
            
            block_index += 1
    return manifest