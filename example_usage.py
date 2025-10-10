"""
Example Usage of CoinGecko-Enhanced Wallet Utilities

This script demonstrates how to use the wallet utilities with CoinGecko API
integration to get token prices and market data before creating swap transactions.
"""

import os
from wallet_utils import (
    load_keypair_from_json,
    get_sol_price,
    get_token_price_by_contract,
    create_swap_transaction
)

def main():
    """
    Example demonstrating CoinGecko integration with wallet utilities.
    """
    
    # Example 1: Get current SOL price
    print("=" * 70)
    print("Example 1: Fetching SOL Price")
    print("=" * 70)
    sol_price = get_sol_price()
    if sol_price:
        print(f"✅ Current SOL price: ${sol_price:.2f}")
    else:
        print("❌ Could not fetch SOL price")
    
    # Example 2: Get token price by contract address
    print("\n" + "=" * 70)
    print("Example 2: Fetching Token Price by Contract")
    print("=" * 70)
    
    # Example: Wrapped SOL (wSOL) - This is a well-known Solana token
    wsol_address = "So11111111111111111111111111111111111111112"
    token_info = get_token_price_by_contract(wsol_address)
    
    if token_info:
        print(f"✅ Token: {token_info['name']} ({token_info['symbol']})")
        print(f"   Price: ${token_info['price']:.2f}")
        print(f"   Market Cap: ${token_info['market_cap']:,.0f}")
        print(f"   24h Volume: ${token_info['24h_vol']:,.0f}")
        print(f"   24h Change: {token_info['24h_change']:.2f}%")
    else:
        print("❌ Could not fetch token information")
        print("   (Token may not be listed on CoinGecko or rate limit reached)")
    
    # Example 3: Create a swap transaction with price information
    # Note: This will fail at the swap instruction step since it's a skeleton
    print("\n" + "=" * 70)
    print("Example 3: Creating Swap Transaction with Price Info")
    print("=" * 70)
    
    try:
        # Load a wallet
        keypair = load_keypair_from_json("wallets/wallet1.json")
        
        # Create a swap transaction (this will show price info but fail at swap instruction)
        # Using Raydium endpoint as an example
        rpc_endpoint = "https://api.mainnet-beta.solana.com"
        
        # Example token address (replace with actual token you want to trade)
        example_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        
        tx = create_swap_transaction(
            keypair=keypair,
            action="buy",
            token_mint_address=example_token,
            amount=0.1,  # 0.1 SOL
            rpc_endpoint=rpc_endpoint,
            slippage_percent=1.5,
            display_price_info=True
        )
        
        print("✅ Transaction created successfully")
        
    except FileNotFoundError:
        print("❌ Wallet file not found. Make sure you have a wallet at wallets/wallet1.json")
    except NotImplementedError as e:
        print(f"\n⚠️  Expected error (skeleton function): {e}")
        print("   This is normal - you need to integrate with a DEX SDK to complete the swap")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nNote: To use the CoinGecko Pro API, set the COINGECKO_PRO_API_KEY")
    print("environment variable with your API key.")
    print("Otherwise, the free tier will be used (with rate limits).")


if __name__ == "__main__":
    main()

