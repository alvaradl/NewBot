"""
Main Entry Point for Solana Trading Bot

This is the main script that initializes and runs the Solana trading bot.
It handles wallet discovery, environment configuration, and provides a foundation
for implementing trading logic.

The bot is designed to work with multiple Solana wallets stored as JSON files
in a designated directory, typically created using solana-keygen.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from wallet_utils import list_public_keys_with_paths


def main() -> None:
    """
    Main function that initializes the trading bot and discovers available wallets.

    This function performs the following operations:
    1. Loads environment variables from .env file (if present)
    2. Sets up the wallets directory
    3. Discovers and validates all available Solana wallets
    4. Displays wallet information to the user

    Environment Variables:
        WALLETS_DIR: Optional. Directory containing wallet JSON files.
                     Defaults to "wallets" if not specified.
        
        RPC_ENDPOINT: Optional. Solana RPC endpoint URL for blockchain interaction.
                      Can be set in .env file or environment.

    Example:
        # Run the bot with default settings
        python main.py
        
        # Run with custom wallets directory
        WALLETS_DIR=my_wallets python main.py
    """
    # Load environment variables from .env file if it exists
    # This allows users to configure settings without modifying code
    # Common variables include RPC_ENDPOINT, WALLETS_DIR, etc.
    load_dotenv()

    # Get the wallets directory from environment variable or use default
    # The WALLETS_DIR environment variable allows users to specify a custom location
    wallets_dir = os.getenv("WALLETS_DIR", "wallets")
    
    # Ensure the wallets directory exists, creating it if necessary
    # This prevents errors when the directory doesn't exist yet
    Path(wallets_dir).mkdir(parents=True, exist_ok=True)

    # Discover all available wallets in the specified directory
    # This function returns a list of (file_path, public_key) tuples
    entries = list_public_keys_with_paths(wallets_dir)
    
    # Check if any wallets were found
    if not entries:
        # Provide helpful instructions for creating wallets
        print(
            f"No wallets found in '{wallets_dir}'. "
            "Create wallets with 'solana-keygen new --outfile wallets\\trader1.json' and re-run."
        )
        return

    # Display all discovered wallets to the user
    print("Discovered wallets:")
    for path_str, pubkey_str in entries:
        # Show each wallet's file path and public key
        # Error messages (if any) are included in pubkey_str
        print(f"- {path_str}: {pubkey_str}")


# Standard Python idiom to run main() when script is executed directly
# This allows the file to be imported as a module without running main()
if __name__ == "__main__":
    main()


