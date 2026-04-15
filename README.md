# pysync

A pure-Python implementation of `rsync`. 

`pysync` is a zero-install, dependency-free remote file synchronization engine. It implements the core differential sync protocol of `rsync` (Andrew Tridgell's rolling hash algorithm using Adler-32 and SHA-256) entirely in Python, ensuring that only the modified binary deltas of a file are transmitted over an SSH tunnel.

The defining architectural feature of `pysync` is its ephemeral deployment model. It requires zero prior installation or configuration on the remote server. When executed, the local orchestrator packages its own source code, pipes it through SSH, bootstraps an ephemeral instance on the remote target, orchestrates the synchronization, and safely destroys the remote execution environment upon completion.

## Architecture

The synchronization process is divided into three distinct, automated phases:

1. **Manifest Pull:** The local orchestrator initiates an SSH tunnel, passing a compressed tarball of the `pysync` source code via `stdin`. The remote server extracts this into a temporary directory, scans the destination file (if it exists), and generates a manifest of its blocks. This manifest and the temporary path are returned to the local machine as a JSON payload.
2. **Delta Calculation:** Using the received manifest, the local engine slides a block-sized window across the updated local file. It calculates rolling hashes to identify identical blocks and novel data, constructing a binary patch stream locally without needing network access.
3. **Atomic Patch:** A second SSH connection is established to the active ephemeral directory. The binary patch is streamed to the remote engine, which reconstructs the file using data from the local stream and blocks from the old file on disk. The reconstruction is written to a hidden temporary file and swapped into production using an atomic rename operation (`os.replace`) to guarantee data integrity against network failures.

## Requirements

**Local Machine:**
* Python 3.8 or higher.
* Standard UNIX utilities: `tar`, `ssh`.
* SSH key-pair authentication configured for the target server.

**Remote Target:**
* Python 3.8 or higher.
* Standard UNIX utilities: `tar`, `mktemp`.
* An active SSH daemon (`sshd`).

## Installation

```bash
git clone https://github.com/gabichulas/pysync.git
cd pysync
```

## Usage

To use `pysync`, you simply run the core file as a usual `rsync`.

```bash
python3 src/pysync.py path/to/local/file user@remote_host:/path/to/destination
```


You can override the default block size (4096 bytes) using the `-b` or `--block-size` flag. Smaller block sizes provide higher granularity for finding matches in highly fragmented files, at the cost of larger manifest sizes and increased CPU overhead.

```bash
python3 src/pysync.py updated_database.sql admin@10.0.0.50:/var/backups/ -b 1024
```

To see more information about the engine, use the `-h` or `--help` flag.

## License

MIT License. See `LICENSE` for more information.