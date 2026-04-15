#!/usr/bin/env python3
import argparse
import os
import sys
import json
import subprocess
from engine import generate_manifest, calculate_delta
from protocol import pack_instruction, unpack_stream

def parse_ssh(target: str):
    if ":" in target:
        conn_info, file_path = target.split(":", 1)
        ssh_prefix = ["ssh", conn_info]
        return True, ssh_prefix, file_path
    return False, [], target

def apply_patch(old_file_path: str, destination_path: str, block_size: int):
    temp_path = f".{os.path.basename(destination_path)}.{os.getpid()}.tmp"
    temp_path = os.path.join(os.path.dirname(destination_path), temp_path)

    old_file = None
    if os.path.exists(old_file_path):
        old_file = open(old_file_path, 'rb')

    try:
        with open(temp_path, 'wb') as out_file:
            for instruction in unpack_stream(sys.stdin.buffer):
                action, payload = instruction
                
                if action == 'LITERAL':
                    out_file.write(payload)
                elif action == 'BLOCK':
                    if not old_file:
                        raise RuntimeError("No existing file in destination")
                    block_index = payload
                    old_file.seek(block_index * block_size)
                    block_data = old_file.read(block_size)
                    out_file.write(block_data)
        
        if old_file:
            old_file.close()
            
        os.replace(temp_path, destination_path)
        
    except Exception as e:
        if old_file:
            old_file.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise e

def main():
    parser = argparse.ArgumentParser(prog="pysync")
    parser.add_argument("--server-manifest", action="store_true", help="Generate manifest")
    parser.add_argument("--server-patch", action="store_true", help="Apply binary delta")
    parser.add_argument("--filename", default="", help="Original file name")
    parser.add_argument("--tmpdir", default="")
    parser.add_argument("source")
    parser.add_argument("destination", nargs='?')
    parser.add_argument("-b", "--block-size", type=int, default=4096)
    args = parser.parse_args()

    if args.server_manifest:
        target_path = args.source
        if os.path.isdir(target_path) and args.filename:
            target_path = os.path.join(target_path, args.filename)
        manifest = generate_manifest(target_path, args.block_size)
        response_payload = {
            "tmpdir": args.tmpdir,
            "manifest": manifest
        }
        print(json.dumps(response_payload))
        sys.exit(0)
        
    elif args.server_patch:
        target_path = args.destination
        if os.path.isdir(target_path) and args.filename:
            target_path = os.path.join(target_path, args.filename)
        
        old_file_path = args.source
        if os.path.isdir(old_file_path) and args.filename:
            old_file_path = os.path.join(old_file_path, args.filename)
            
        apply_patch(old_file_path, target_path, args.block_size)
        sys.exit(0)
        
    else:
        is_remote, ssh_prefix, remote_path = parse_ssh(args.destination)
        
        if not is_remote:
            print("Error: The destination must be a remote SSH target (user@host:/path)")
            sys.exit(1)
        
        src_dir = os.path.dirname(os.path.abspath(__file__))
        local_filename = os.path.basename(args.source)
        
        tar_cmd = ["tar", "-czf", "-", "-C", src_dir, "."]
        
        remote_script = f"""
        set -e
        TMP_DIR=$(mktemp -d -t pysync_XXXXXX)
        tar -xzf - -C $TMP_DIR
        cd $TMP_DIR
        python3 pysync.py --server-manifest "{remote_path}" --filename "{local_filename}" --tmpdir "$TMP_DIR" -b {args.block_size}
        """
        
        ssh_cmd = ssh_prefix + [remote_script]
        
        try:
            p_tar = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE)
            p_ssh = subprocess.Popen(ssh_cmd, stdin=p_tar.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_tar.stdout.close()
            
            stdout_data, stderr_data = p_ssh.communicate()
            
            if p_ssh.returncode != 0:
                print(f"[!] Remote error:\n{stderr_data.decode()}")
                sys.exit(1)
                
            try:
                remote_response = json.loads(stdout_data.decode())
                raw_manifest = remote_response["manifest"]
                remote_tmpdir = remote_response["tmpdir"]
                remote_manifest = {int(k): v for k, v in raw_manifest.items()}
                
                delta_stream = calculate_delta(args.source, remote_manifest, args.block_size)
                binary_patch = b""
                for action, payload in delta_stream:
                    binary_patch += pack_instruction(action, payload)
            except json.decoder.JSONDecodeError:
                sys.exit(1)
            
            remote_patch_script = f"""
            set -e
            cd {remote_tmpdir}
            python3 pysync.py --server-patch "{remote_path}" "{remote_path}" --filename "{local_filename}" -b {args.block_size}
            rm -rf {remote_tmpdir}
            """
            
            patch_cmd = ssh_prefix + [remote_patch_script]
            
            p_patch = subprocess.Popen(patch_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            _, patch_stderr = p_patch.communicate(input=binary_patch)
            
            if p_patch.returncode != 0:
                print(f"[!] Error:\n{patch_stderr.decode()}")
                sys.exit(1)
                
            print("Success")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()