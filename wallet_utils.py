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
from typing import List, Tuple, Literal

from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solders.transaction import Transaction
from solders.message import Message
from solders.instruction import Instruction


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


def create_swap_transaction(
    keypair: Keypair,
    action: Literal["buy", "sell"],
    token_mint_address: str,
    amount: float,
    rpc_endpoint: str,
) -> Transaction:
    """
    Creates a skeleton for a buy or sell swap transaction on a DEX.

    THIS IS A SKELETON FUNCTION. It requires a DEX-specific implementation
    to find the liquidity pool and build the correct swap instruction.

    Args:
        keypair: The keypair of the wallet executing the swap.
        action: The action to perform, either "buy" or "sell".
        token_mint_address: The mint address of the token to trade.
        amount: The amount of SOL to spend (for a buy) or the amount of
                the token to sell.
        rpc_endpoint: The Solana RPC endpoint URL.

    Returns:
        Transaction: A Solana transaction object, ready to be signed and sent.

    Raises:
        NotImplementedError: As this is a skeleton function.
        ValueError: If the action is not 'buy' or 'sell'.
    """
    client = Client(rpc_endpoint)
    token_mint = Pubkey.from_string(token_mint_address)
    owner = keypair.pubkey()

    print(f"Preparing to {action} {amount} of {token_mint_address} for wallet {owner}")

    # 1. (DEX-SPECIFIC) Find the liquidity pool for the token pair.
    # -----------------------------------------------------------------
    # This is the most critical and complex part. You need to interact with your
    # chosen DEX (e.g., Raydium, Orca) to find the market ID or liquidity
    # pool address for the SOL-Token pair.
    #
    # Example (conceptual):
    # liquidity_pool_address = find_raydium_pool(token_mint_address)
    # if not liquidity_pool_address:
    #     raise ValueError("Liquidity pool not found for the given token.")
    #
    print("Step 1: Find liquidity pool (DEX-specific implementation required)")
    # Placeholder - replace with actual DEX API call
    liquidity_pool_address = Pubkey.new_unique()  # Replace this line

    # 2. (DEX-SPECIFIC) Construct the swap instruction.
    # -----------------------------------------------------------------
    # This involves creating a `TransactionInstruction` with the correct program ID
    # for your DEX's swap program and encoding the instruction data correctly.
    # The data will include the amount, slippage, and accounts involved.
    #
    # Example (conceptual):
    # swap_instruction = create_raydium_swap_instruction(
    #     user_wallet=owner,
    #     pool_address=liquidity_pool_address,
    #     token_mint=token_mint,
    #     amount_in=amount,
    #     action=action,
    #     slippage_percent=1.0  # 1% slippage tolerance
    # )
    #
    print("Step 2: Construct swap instruction (DEX-specific implementation required)")
    # Placeholder - replace with actual DEX instruction builder
    swap_instruction = None  # Replace this line
    if swap_instruction is None:
        raise NotImplementedError("Swap instruction creation is not implemented.")


    # 3. Get the latest blockhash.
    # -----------------------------------------------------------------
    # Every transaction needs a recent blockhash to be valid.
    print("Step 3: Fetching latest blockhash")
    blockhash_resp = client.get_latest_blockhash()
    latest_blockhash = blockhash_resp.value.blockhash

    # 4. Assemble the transaction.
    # -----------------------------------------------------------------
    # Create a new transaction and add the swap instruction.
    print("Step 4: Assembling the transaction")
    message = Message.new_with_blockhash(
        [swap_instruction],
        owner,
        latest_blockhash
    )
    transaction = Transaction(
        [keypair],
        message,
        latest_blockhash
    )

    # The transaction is now ready to be signed by the keypair and sent.
    # Example of sending:
    #
    # transaction.sign([keypair])
    # tx_signature = client.send_transaction(transaction).value
    # print(f"Transaction sent with signature: {tx_signature}")

    return transaction