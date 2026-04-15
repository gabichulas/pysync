import struct

ACTION_BLOCK = 1
ACTION_LITERAL = 2

def pack_instruction(action: str, payload) -> bytes:
    if action == 'BLOCK':
        instruction = struct.pack('!BI', ACTION_BLOCK, payload)
        return instruction
    elif action == 'LITERAL':
        instruction = struct.pack('!BI', ACTION_LITERAL, len(payload))
        return instruction + payload
    else:
        raise ValueError(f"Unknown action: {action}")

def unpack_stream(network_stream):
    while True:
        header_bytes = network_stream.read(5)
        if not header_bytes:
            break
            
        action_type, parameter = struct.unpack('!BI', header_bytes)
        
        if action_type == ACTION_BLOCK:
            yield ('BLOCK', parameter)
            
        elif action_type == ACTION_LITERAL:
            payload_length = parameter
            raw_data = network_stream.read(payload_length)
            yield ('LITERAL', raw_data)