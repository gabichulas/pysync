import hashlib
import os
import zlib

def get_strong_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def get_weak_hash(data: bytes) -> int:
    return zlib.adler32(data)

def generate_manifest(file_path: str, block_size: int) -> dict:

    manifest = {}
    
    if not os.path.exists(file_path):
        return manifest
        
    with open(file_path, 'rb') as f:
        block_index = 0
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
                
            weak = get_weak_hash(chunk)
            strong = get_strong_hash(chunk)
            
            if weak not in manifest:
                manifest[weak] = []
                
            manifest[weak].append((block_index, strong))
            block_index += 1
            
    return manifest

def calculate_delta(new_file_path: str, manifest: dict, block_size: int, progress_callback=None):

    literal_buffer = bytearray()
    
    with open(new_file_path, 'rb') as f:
        new_data = f.read()
        
    cursor = 0
    file_length = len(new_data)
    last_reported_percent = -1

    def report_progress():
        nonlocal last_reported_percent
        if not progress_callback or file_length == 0:
            return

        current_percent = int((cursor / file_length) * 100)
        if current_percent != last_reported_percent:
            last_reported_percent = current_percent
            progress_callback(cursor, file_length)
    
    while cursor < file_length:
        report_progress()
        window = new_data[cursor : cursor + block_size]
        
        if len(window) < block_size:
            literal_buffer.extend(window)
            cursor = file_length
            report_progress()
            break
            
        weak = get_weak_hash(window)
        match_found = False
        
        if weak in manifest:
            strong = get_strong_hash(window)
            
            for block_index, remote_strong in manifest[weak]:
                if strong == remote_strong:
                    match_found = True
                    
                    if literal_buffer:
                        yield ('LITERAL', bytes(literal_buffer))
                        literal_buffer.clear()
                        
                    yield ('BLOCK', block_index)
                    
                    cursor += block_size
                    report_progress()
                    break
                    
        if not match_found:
            literal_buffer.append(new_data[cursor])
            cursor += 1
            report_progress()
            
    if literal_buffer:
        yield ('LITERAL', bytes(literal_buffer))