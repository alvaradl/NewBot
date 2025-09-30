"""
Wallet Utilities Module for Solana Trading Bot (macOS version)

This module provides utilities for loading and managing Solana keypairs (wallets)
from JSON files on macOS. It is almost identical to the cross-platform version,
but notes macOS path handling and Python environment differences.

Key Concepts:
- Solana keypairs consist of a 32-byte seed (private key) and 32-byte public key
- solana-keygen outputs keypairs as JSON arrays of 64 integers (64 bytes total)
- The solders library is used for Solana cryptography operations
"""

import json
import os
from pathlib import Path
from typing import List, Tuple

from solders.keypair import Keypair


def load_keypair_from_json(json_path: os.PathLike | str) -> Keypair:
    """
    Load a Solana Keypair from a JSON file produced by solana-keygen.

    macOS Notes:
      - Paths like ~/wallets are expanded automatically.
      - Ensure the JSON file is a 64-byte array (standard solana-keygen output).

    Args:
        json_path: Path to the JSON file (can include ~ for home dir).

    Returns:
        Keypair: Solana keypair object usable for transactions.
    """
    # Expand ~ and ensure correct path object
    path = Path(json_path).expanduser()

    if not path.exists():
        raise FileNotFoundError(f"Wallet file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, list):
        raise ValueError(f"Invalid key file format (expected array): {path}")

    secret_key_bytes = bytes(raw)

    if len(secret_key_bytes) not in (64, 32):
        raise ValueError(
            f"Unexpected secret key length {len(secret_key_bytes)} in {path}"
        )

    return Keypair.from_bytes(secret_key_bytes)


def load_all_wallets(wallets_dir: os.PathLike | str = "wallets") -> List[Keypair]:
    """
    Load all wallets from a directory.

    macOS Notes:
      - ~/wallets expands to /Users/<you>/wallets
      - Works recursively for subdirectories.
    """
    base = Path(wallets_dir).expanduser()
    if not base.exists():
        return []

    keypairs: List[Keypair] = []
    for json_file in sorted(base.glob("**/*.json")):
        try:
            kp = load_keypair_from_json(json_file)
            keypairs.append(kp)
        except Exception as exc:
            print(f"Failed to load {json_file}: {exc}")

    return keypairs


def list_public_keys_with_paths(wallets_dir: os.PathLike | str = "wallets") -> List[Tuple[str, str]]:
    """
    Return [(file_path, public_key_string)] for each wallet.

    macOS Notes:
      - Paths are absolute when expanded.
    """
    base = Path(wallets_dir).expanduser()
    results: List[Tuple[str, str]] = []

    if not base.exists():
        return results

    for json_file in sorted(base.glob("**/*.json")):
        try:
            kp = load_keypair_from_json(json_file)
            results.append((str(json_file), str(kp.pubkey())))
        except Exception as exc:
            results.append((str(json_file), f"<error: {exc}>"))

    return results
