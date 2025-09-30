"""
Wallet Utilities Module for Solana Trading Bot

This module provides utilities for loading and managing Solana keypairs (wallets)
from JSON files. It handles the conversion from the JSON format used by 
solana-keygen to the Keypair objects needed for Solana transactions.

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

    This function reads a JSON file containing a Solana keypair and converts it
    into a Keypair object that can be used for signing transactions.

    Args:
        json_path: Path to the JSON file containing the keypair data.
                  The file should contain a JSON array of 64 integers representing
                  the keypair bytes (32-byte seed + 32-byte public key).

    Returns:
        Keypair: A Solana keypair object that can be used for transactions.

    Raises:
        ValueError: If the file format is invalid or the key length is unexpected.
        FileNotFoundError: If the specified file doesn't exist.

    Example:
        # File wallets/trader1.json contains: [43,115,226,141,251,12,67,76,...]
        keypair = load_keypair_from_json("wallets/trader1.json")
        public_key = keypair.pubkey()  # Get the public key
    """
    # Convert the input path to a Path object for easier manipulation
    path = Path(json_path)
    
    # Read and parse the JSON file content
    # The file should contain an array of integers representing bytes
    raw = json.loads(path.read_text(encoding="utf-8"))
    
    # Validate that the JSON contains an array (list of integers)
    if not isinstance(raw, list):
        raise ValueError(f"Invalid key file format (expected array): {path}")
    
    # Convert the list of integers to bytes
    # Each integer represents one byte of the keypair
    secret_key_bytes = bytes(raw)
    
    # Validate the key length - Solana keypairs should be exactly 64 bytes
    # (32 bytes for the seed/private key + 32 bytes for the public key)
    # Some tools might output only 32 bytes (seed only), so we accept both
    if len(secret_key_bytes) not in (64, 32):
        # solana-keygen typically outputs 64-byte secret key arrays
        raise ValueError(
            f"Unexpected secret key length {len(secret_key_bytes)} in {path}"
        )
    
    # Create and return a Keypair object using the solders library
    # from_bytes() is the correct method to reconstruct a keypair from raw bytes
    return Keypair.from_bytes(secret_key_bytes)


def load_all_wallets(wallets_dir: os.PathLike | str = "wallets") -> List[Keypair]:
    """
    Load all Solana keypairs from a directory containing JSON wallet files.

    This function scans a directory for all JSON files and attempts to load them
    as Solana keypairs. It's designed to be robust - if one wallet file is corrupted
    or invalid, it will continue processing the others and report the error.

    Args:
        wallets_dir: Path to the directory containing wallet JSON files.
                    Defaults to "wallets" directory in the current working directory.

    Returns:
        List[Keypair]: A list of successfully loaded keypair objects.
                      Empty list if no valid wallets are found or directory doesn't exist.

    Example:
        # Load all wallets from the default "wallets" directory
        wallets = load_all_wallets()
        
        # Load all wallets from a custom directory
        wallets = load_all_wallets("my_wallets")
        
        # Process each wallet
        for wallet in wallets:
            print(f"Wallet public key: {wallet.pubkey()}")
    """
    # Create a Path object for the wallets directory
    base = Path(wallets_dir)
    
    # If the directory doesn't exist, return an empty list
    if not base.exists():
        return []
    
    # List to store successfully loaded keypairs
    keypairs: List[Keypair] = []
    
    # Search for all JSON files in the directory (including subdirectories)
    # Sort them to ensure consistent ordering
    for json_file in sorted(base.glob("**/*.json")):
        try:
            # Attempt to load the keypair from this JSON file
            kp = load_keypair_from_json(json_file)
            keypairs.append(kp)
        except Exception as exc:  # keep going; report invalid files later
            # If loading fails, print an error but continue with other files
            print(f"Failed to load {json_file}: {exc}")
    
    return keypairs


def list_public_keys_with_paths(wallets_dir: os.PathLike | str = "wallets") -> List[Tuple[str, str]]:
    """
    Get a list of wallet file paths and their corresponding public keys.

    This function is useful for displaying wallet information without actually loading
    the full keypair objects into memory. It returns a list of tuples containing
    the file path and the public key string for each wallet.

    Unlike load_all_wallets(), this function returns error information in the results
    rather than printing errors to console, making it suitable for UI display.

    Args:
        wallets_dir: Path to the directory containing wallet JSON files.
                    Defaults to "wallets" directory in the current working directory.

    Returns:
        List[Tuple[str, str]]: A list of tuples where each tuple contains:
                               - File path as a string
                               - Public key as a string (or error message if loading failed)

    Example:
        # Get wallet information for display
        wallet_info = list_public_keys_with_paths()
        
        # Display the results
        for file_path, pubkey in wallet_info:
            if pubkey.startswith("<error:"):
                print(f"❌ {file_path}: {pubkey}")
            else:
                print(f"✅ {file_path}: {pubkey}")
    """
    # Create a Path object for the wallets directory
    base = Path(wallets_dir)
    
    # List to store results as (file_path, public_key_or_error) tuples
    results: List[Tuple[str, str]] = []
    
    # If the directory doesn't exist, return empty results
    if not base.exists():
        return results
    
    # Search for all JSON files in the directory (including subdirectories)
    # Sort them to ensure consistent ordering
    for json_file in sorted(base.glob("**/*.json")):
        try:
            # Attempt to load the keypair from this JSON file
            kp = load_keypair_from_json(json_file)
            # Extract the public key and convert to string
            public_key_str = str(kp.pubkey())
            results.append((str(json_file), public_key_str))
        except Exception as exc:
            # If loading fails, include error information in the results
            # This allows the caller to handle errors appropriately
            results.append((str(json_file), f"<error: {exc}>"))
    
    return results


