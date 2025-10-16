"""
Interactive Solana Token Swap Interface

This script provides an interactive command-line interface for swapping tokens
on Solana using Jupiter aggregator with CoinGecko price validation.

Features:
- Displays wallet balance
- Interactive token swap with buy/sell options
- Real-time price information from CoinGecko
- Jupiter aggregator for best swap routes
- Comprehensive error handling
"""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from solana.rpc.api import Client
from solders.keypair import Keypair

from wallet_utils import (
    load_keypair_from_json,
    list_public_keys_with_paths,
    # CoinGecko functions disabled for now:
    # get_sol_price,
    # get_token_price_by_contract
)


def get_sol_balance(client: Client, keypair: Keypair) -> Optional[float]:
    """
    Get the SOL balance for a wallet.
    
    Args:
        client: Solana RPC client
        keypair: Wallet keypair
    
    Returns:
        Optional[float]: Balance in SOL (not lamports), or None on error
    """
    try:
        response = client.get_balance(keypair.pubkey())
        if response.value is not None:
            # Convert lamports to SOL (1 SOL = 1,000,000,000 lamports)
            return response.value / 1_000_000_000
        return None
    except Exception as e:
        print(f"  Error fetching balance: {e}")
        return None


def display_wallet_info(client: Client, keypair: Keypair) -> None:
    """
    Display wallet information including address and balance.
    
    Args:
        client: Solana RPC client
        keypair: Wallet keypair
    """
    print("\n" + "=" * 70)
    print("WALLET INFORMATION")
    print("=" * 70)
    print(f"Address: {keypair.pubkey()}")
    
    # Get SOL balance
    balance = get_sol_balance(client, keypair)
    if balance is not None:
        print(f"Balance: {balance:.4f} SOL")
        # USD price display disabled - will add alternative API later
    else:
        print("Balance: Unable to fetch")
    
    print("=" * 70)


def get_user_input(prompt: str, required: bool = True) -> Optional[str]:
    """
    Get user input with optional validation.
    
    Args:
        prompt: Prompt message to display
        required: If True, keep asking until input is provided
    
    Returns:
        Optional[str]: User input or None
    """
    while True:
        user_input = input(prompt).strip()
        
        if user_input:
            return user_input
        
        if not required:
            return None
        
        print("  This field is required. Please enter a value.")


def get_action_choice() -> Optional[str]:
    """
    Get user's choice of buy or sell action.
    
    Returns:
        Optional[str]: "buy" or "sell", or None to cancel
    """
    print("\n" + "=" * 70)
    print("SWAP ACTION")
    print("=" * 70)
    print("1. Buy token with SOL")
    print("2. Sell token for SOL")
    print("0. Cancel")
    
    while True:
        choice = input("\nEnter your choice (0-2): ").strip()
        
        if choice == "0":
            return None
        elif choice == "1":
            return "buy"
        elif choice == "2":
            return "sell"
        else:
            print("  Invalid choice. Please enter 0, 1, or 2.")


def get_token_mint_address() -> Optional[str]:
    """
    Get token mint address from user with common token shortcuts.
    
    Returns:
        Optional[str]: Token mint address or None to cancel
    """
    print("\n" + "=" * 70)
    print("TOKEN SELECTION")
    print("=" * 70)
    print("Common tokens:")
    print("  USDC  - USD Coin")
    print("  USDT  - Tether USD")
    print("  RAY   - Raydium")
    print("  ORCA  - Orca")
    print("\nOr enter any Solana token mint address")
    print("(Enter 'cancel' to go back)")
    
    # Common token shortcuts
    COMMON_TOKENS = {
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"
    }
    
    while True:
        token_input = input("\nToken (symbol or mint address): ").strip()
        
        if token_input.lower() == "cancel":
            return None
        
        # Check if it's a common token shortcut
        if token_input.upper() in COMMON_TOKENS:
            mint_address = COMMON_TOKENS[token_input.upper()]
            print(f" Selected {token_input.upper()}: {mint_address}")
            return mint_address
        
        # Validate mint address format (basic check - 32-44 chars, base58)
        if len(token_input) >= 32 and len(token_input) <= 44:
            # Basic validation only (CoinGecko disabled for now)
            print(" Token address format valid")
            return token_input
        else:
            print("  Invalid mint address format. Must be 32-44 characters.")

def select_wallet(wallets_dir: str) -> Optional[Keypair]:
    """
    Let user select a wallet from available wallets.
    
    Args:
        wallets_dir: Directory containing wallet files
    
    Returns:
        Optional[Keypair]: Selected wallet keypair or None
    """
    entries = list_public_keys_with_paths(wallets_dir)
    
    if not entries:
        print(f"\n No wallets found in '{wallets_dir}'")
        print("\nTo create a wallet:")
        print(f"  solana-keygen new --outfile {wallets_dir}\\wallet1.json")
        return None
    
    print("\n" + "=" * 70)
    print("AVAILABLE WALLETS")
    print("=" * 70)
    
    valid_wallets = []
    for i, (path_str, pubkey_str) in enumerate(entries, 1):
        if not pubkey_str.startswith("<error:"):
            print(f"{i}. {Path(path_str).name}")
            print(f"   {pubkey_str}")
            valid_wallets.append(path_str)
        else:
            print(f"{i}. {Path(path_str).name} - ERROR: {pubkey_str}")
    
    if not valid_wallets:
        print("\n No valid wallets found")
        return None
    
    print("=" * 70)
    
    # If only one wallet, use it
    if len(valid_wallets) == 1:
        wallet_path = valid_wallets[0]
        print(f"\n Using wallet: {Path(wallet_path).name}")
    else:
        # Let user choose
        while True:
            try:
                choice = input(f"\nSelect wallet (1-{len(valid_wallets)}): ").strip()
                idx = int(choice) - 1
                
                if 0 <= idx < len(valid_wallets):
                    wallet_path = valid_wallets[idx]
                    break
                else:
                    print(f"  Please enter a number between 1 and {len(valid_wallets)}")
            except ValueError:
                print("  Please enter a valid number")
    
    # Load the wallet
    try:
        keypair = load_keypair_from_json(wallet_path)
        print(" Wallet loaded successfully")
        return keypair
    except Exception as e:
        print(f" Failed to load wallet: {e}")
        return None


def main() -> None:
    """
    Main interactive swap interface.
    """
    # Load environment variables
    load_dotenv()
    
    # Get configuration
    wallets_dir = os.getenv("WALLETS_DIR", "wallets")
    rpc_endpoint = os.getenv("RPC_ENDPOINT", "https://api.mainnet-beta.solana.com")
    
    # Ensure wallets directory exists
    Path(wallets_dir).mkdir(parents=True, exist_ok=True)
    
    # Select wallet
    keypair = select_wallet(wallets_dir)
    if not keypair:
        return
    
    # Create RPC client
    client = Client(rpc_endpoint)
    
    # Display wallet info and balance
    display_wallet_info(client, keypair)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n Fatal error: {e}")
        sys.exit(1)
