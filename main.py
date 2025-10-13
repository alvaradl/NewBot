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
    create_swap_transaction,
    get_sol_price,
    get_token_price_by_contract
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
        print(f"⚠️  Error fetching balance: {e}")
        return None


def display_wallet_info(client: Client, keypair: Keypair) -> None:
    """
    Display wallet information including address and balance.
    
    Args:
        client: Solana RPC client
        keypair: Wallet keypair
    """
    print("\n" + "=" * 70)
    print("💼 WALLET INFORMATION")
    print("=" * 70)
    print(f"Address: {keypair.pubkey()}")
    
    # Get SOL balance
    balance = get_sol_balance(client, keypair)
    if balance is not None:
        print(f"Balance: {balance:.4f} SOL")
        
        # Show USD value if we can get SOL price
        sol_price = get_sol_price()
        if sol_price:
            usd_value = balance * sol_price
            print(f"         ~${usd_value:.2f} USD (at ${sol_price:.2f}/SOL)")
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
        
        print("⚠️  This field is required. Please enter a value.")


def get_action_choice() -> Optional[str]:
    """
    Get user's choice of buy or sell action.
    
    Returns:
        Optional[str]: "buy" or "sell", or None to cancel
    """
    print("\n" + "=" * 70)
    print("📊 SWAP ACTION")
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
            print("⚠️  Invalid choice. Please enter 0, 1, or 2.")


def get_token_mint_address() -> Optional[str]:
    """
    Get token mint address from user with common token shortcuts.
    
    Returns:
        Optional[str]: Token mint address or None to cancel
    """
    print("\n" + "=" * 70)
    print("🪙 TOKEN SELECTION")
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
            print(f"✅ Selected {token_input.upper()}: {mint_address}")
            return mint_address
        
        # Validate mint address format (basic check - 32-44 chars, base58)
        if len(token_input) >= 32 and len(token_input) <= 44:
            # Try to fetch token info to validate
            print("🔍 Validating token address...")
            token_info = get_token_price_by_contract(token_input)
            
            if token_info:
                print(f"✅ Token found: {token_info['name']} ({token_info['symbol']})")
                print(f"   Current price: ${token_info['price']:.6f}")
                return token_input
            else:
                print("⚠️  Token not found on CoinGecko (may still be valid)")
                confirm = input("   Continue anyway? (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    return token_input
                else:
                    print("   Please try a different token.")
        else:
            print("⚠️  Invalid mint address format. Must be 32-44 characters.")


def get_amount(action: str, balance: Optional[float]) -> Optional[float]:
    """
    Get swap amount from user with validation.
    
    Args:
        action: "buy" or "sell"
        balance: Current SOL balance for validation
    
    Returns:
        Optional[float]: Amount to swap, or None to cancel
    """
    print("\n" + "=" * 70)
    print("💰 SWAP AMOUNT")
    print("=" * 70)
    
    if action == "buy":
        print("How much SOL do you want to spend?")
        if balance:
            print(f"Available balance: {balance:.4f} SOL")
            print(f"(Keep some for transaction fees, recommend max: {balance - 0.01:.4f} SOL)")
    else:
        print("How many tokens do you want to sell?")
        print("(Amount in whole token units, not lamports)")
    
    print("(Enter 'cancel' to go back)")
    
    while True:
        amount_input = input("\nAmount: ").strip()
        
        if amount_input.lower() == "cancel":
            return None
        
        try:
            amount = float(amount_input)
            
            if amount <= 0:
                print("⚠️  Amount must be greater than 0")
                continue
            
            # Validate SOL amount for buy action
            if action == "buy" and balance is not None:
                if amount > balance:
                    print(f"⚠️  Insufficient balance. You have {balance:.4f} SOL")
                    continue
                
                if amount > balance - 0.01:
                    print("⚠️  Leave at least 0.01 SOL for transaction fees")
                    print(f"   Recommended max: {balance - 0.01:.4f} SOL")
                    continue
            
            return amount
            
        except ValueError:
            print("⚠️  Invalid amount. Please enter a number (e.g., 0.5)")


def get_slippage() -> float:
    """
    Get slippage tolerance from user with presets.
    
    Returns:
        float: Slippage percentage
    """
    print("\n" + "=" * 70)
    print("⚙️  SLIPPAGE TOLERANCE")
    print("=" * 70)
    print("1. Low (0.5%)     - For stablecoins")
    print("2. Medium (1%)    - Recommended for most tokens")
    print("3. High (2%)      - For volatile tokens")
    print("4. Custom")
    
    while True:
        choice = input("\nSelect slippage (1-4) [default: 2]: ").strip()
        
        if not choice or choice == "2":
            return 1.0
        elif choice == "1":
            return 0.5
        elif choice == "3":
            return 2.0
        elif choice == "4":
            while True:
                try:
                    custom = float(input("Enter slippage % (e.g., 1.5): ").strip())
                    if 0 < custom <= 10:
                        return custom
                    else:
                        print("⚠️  Slippage must be between 0 and 10%")
                except ValueError:
                    print("⚠️  Invalid number")
        else:
            print("⚠️  Invalid choice. Please enter 1-4.")


def confirm_swap(action: str, token_address: str, amount: float, slippage: float) -> bool:
    """
    Ask user to confirm the swap details.
    
    Args:
        action: "buy" or "sell"
        token_address: Token mint address
        amount: Amount to swap
        slippage: Slippage tolerance
    
    Returns:
        bool: True to proceed, False to cancel
    """
    print("\n" + "=" * 70)
    print("⚠️  CONFIRM SWAP DETAILS")
    print("=" * 70)
    print(f"Action:    {action.upper()}")
    print(f"Token:     {token_address}")
    print(f"Amount:    {amount} {'SOL' if action == 'buy' else 'tokens'}")
    print(f"Slippage:  {slippage}%")
    print("=" * 70)
    
    while True:
        confirm = input("\nProceed with swap? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            return True
        elif confirm in ['no', 'n']:
            return False
        else:
            print("⚠️  Please enter 'yes' or 'no'")


def execute_swap(
    keypair: Keypair,
    action: str,
    token_mint_address: str,
    amount: float,
    slippage: float,
    rpc_endpoint: str
) -> bool:
    """
    Execute the token swap.
    
    Args:
        keypair: Wallet keypair
        action: "buy" or "sell"
        token_mint_address: Token mint address
        amount: Amount to swap
        slippage: Slippage tolerance
        rpc_endpoint: Solana RPC endpoint
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("\n" + "=" * 70)
        print("🔄 EXECUTING SWAP")
        print("=" * 70)
        
        # Create the swap transaction
        transaction = create_swap_transaction(
            keypair=keypair,
            action=action,
            token_mint_address=token_mint_address,
            amount=amount,
            rpc_endpoint=rpc_endpoint,
            slippage_percent=slippage,
            display_price_info=True
        )
        
        # Ask if user wants to send the transaction
        print("\n" + "=" * 70)
        send = input("Send transaction to network? (yes/no): ").strip().lower()
        
        if send in ['yes', 'y']:
            # Ask about skipping preflight for volatile tokens
            skip_preflight = False
            if slippage >= 5.0:  # High slippage suggests volatile token
                print("\n⚠️  High slippage detected - this might be a volatile token (e.g., Pump.fun)")
                skip_option = input("Skip preflight check? (recommended for volatile tokens) (yes/no): ").strip().lower()
                skip_preflight = skip_option in ['yes', 'y']
                if skip_preflight:
                    print("ℹ️  Skipping preflight simulation - transaction will be sent directly")
            
            client = Client(rpc_endpoint)
            
            # Send with or without preflight based on user choice
            from solana.rpc.types import TxOpts
            from solana.rpc.commitment import Confirmed
            opts = TxOpts(skip_preflight=skip_preflight)
            
            print("\n📤 Sending transaction...")
            result = client.send_transaction(transaction, opts=opts)
            signature = result.value
            
            print(f"📤 Transaction sent: {signature}")
            print("⏳ Waiting for confirmation...")
            
            # Wait for confirmation and check if it actually succeeded
            try:
                confirmation = client.confirm_transaction(signature, commitment=Confirmed)
                
                # Check if transaction succeeded on-chain
                if confirmation.value[0].err is None:
                    print("\n" + "=" * 70)
                    print("✅ SWAP SUCCESSFUL!")
                    print("=" * 70)
                    print(f"Transaction signature: {signature}")
                    print(f"View on Solscan: https://solscan.io/tx/{signature}")
                    print("=" * 70)
                    return True
                else:
                    # Transaction failed on-chain
                    error_info = confirmation.value[0].err
                    print("\n" + "=" * 70)
                    print("❌ SWAP FAILED ON-CHAIN")
                    print("=" * 70)
                    print(f"Transaction was sent but failed: {error_info}")
                    print("\n⚠️  You lost transaction fees but the swap didn't execute")
                    print(f"View details: https://solscan.io/tx/{signature}")
                    print("\nCommon reasons:")
                    print("- Price moved beyond slippage tolerance (very common with Pump.fun)")
                    print("- Insufficient token balance")
                    print("- Pool liquidity changed")
                    print("- Try again immediately with fresh quote")
                    print("=" * 70)
                    return False
                    
            except Exception as e:
                print(f"\n⚠️  Could not confirm transaction: {e}")
                print(f"Check status manually: https://solscan.io/tx/{signature}")
                return False
        else:
            print("\n❌ Transaction cancelled by user")
            return False
            
    except ValueError as e:
        print("\n" + "=" * 70)
        print("❌ SWAP FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print("\nPossible solutions:")
        print("- Check if token pair has sufficient liquidity")
        print("- Try increasing slippage tolerance")
        print("- Verify token mint address is correct")
        print("- Check your internet connection")
        print("=" * 70)
        return False
    
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ UNEXPECTED ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        print("=" * 70)
        return False


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
        print(f"\n❌ No wallets found in '{wallets_dir}'")
        print("\nTo create a wallet:")
        print(f"  solana-keygen new --outfile {wallets_dir}\\wallet1.json")
        return None
    
    print("\n" + "=" * 70)
    print("💼 AVAILABLE WALLETS")
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
        print("\n❌ No valid wallets found")
        return None
    
    print("=" * 70)
    
    # If only one wallet, use it
    if len(valid_wallets) == 1:
        wallet_path = valid_wallets[0]
        print(f"\n✅ Using wallet: {Path(wallet_path).name}")
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
                    print(f"⚠️  Please enter a number between 1 and {len(valid_wallets)}")
            except ValueError:
                print("⚠️  Please enter a valid number")
    
    # Load the wallet
    try:
        keypair = load_keypair_from_json(wallet_path)
        print("✅ Wallet loaded successfully")
        return keypair
    except Exception as e:
        print(f"❌ Failed to load wallet: {e}")
        return None


def main() -> None:
    """
    Main interactive swap interface.
    """
    # Load environment variables
    load_dotenv()
    
    # Print welcome banner
    print("\n" + "=" * 70)
    print("🚀 SOLANA TOKEN SWAP INTERFACE")
    print("=" * 70)
    print("Powered by Jupiter Aggregator + CoinGecko")
    print("=" * 70)
    
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
    balance = get_sol_balance(client, keypair)
    
    # Main swap loop
    while True:
        print("\n" + "=" * 70)
        print("MAIN MENU")
        print("=" * 70)
        print("1. Create Token Swap")
        print("2. View Balance")
        print("0. Exit")
        
        choice = input("\nEnter choice: ").strip()
        
        if choice == "0":
            print("\n👋 Goodbye!")
            break
        
        elif choice == "2":
            display_wallet_info(client, keypair)
            balance = get_sol_balance(client, keypair)
        
        elif choice == "1":
            # Get swap action
            action = get_action_choice()
            if not action:
                continue
            
            # Get token mint address
            token_mint = get_token_mint_address()
            if not token_mint:
                continue
            
            # Get amount
            amount = get_amount(action, balance)
            if not amount:
                continue
            
            # Get slippage
            slippage = get_slippage()
            
            # Confirm swap
            if not confirm_swap(action, token_mint, amount, slippage):
                print("\n❌ Swap cancelled")
                continue
            
            # Execute swap
            success = execute_swap(
                keypair=keypair,
                action=action,
                token_mint_address=token_mint,
                amount=amount,
                slippage=slippage,
                rpc_endpoint=rpc_endpoint
            )
            
            if success:
                # Update balance
                balance = get_sol_balance(client, keypair)
        
        else:
            print("⚠️  Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        sys.exit(1)
