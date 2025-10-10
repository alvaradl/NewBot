"""
Complete Example: Token Swap with Jupiter + CoinGecko Integration

This script demonstrates how to use the fully integrated swap functionality
that combines Jupiter aggregator (for actual swaps) with CoinGecko (for price data).
"""

import os
from wallet_utils import (
    load_keypair_from_json,
    create_swap_transaction,
    get_sol_price,
    get_token_price_by_contract
)


def example_buy_token():
    """
    Example: Buy USDC with SOL using Jupiter aggregator
    """
    print("=" * 80)
    print("EXAMPLE 1: BUY TOKEN (SOL → USDC)")
    print("=" * 80)
    
    try:
        # Load your wallet
        keypair = load_keypair_from_json("wallets/wallet1.json")
        print(f"✅ Wallet loaded: {keypair.pubkey()}\n")
        
        # USDC mint address on Solana
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # Create swap transaction
        # This will:
        # 1. Show CoinGecko price data
        # 2. Get the best route from Jupiter
        # 3. Build and sign the transaction
        transaction = create_swap_transaction(
            keypair=keypair,
            action="buy",
            token_mint_address=usdc_mint,
            amount=0.01,  # Spend 0.01 SOL
            rpc_endpoint="https://api.mainnet-beta.solana.com",
            slippage_percent=1.0,  # 1% slippage tolerance
            display_price_info=True
        )
        
        print("\n✅ Transaction created and signed!")
        print("⚠️  To actually send it, uncomment the following code:")
        print("""
        from solana.rpc.api import Client
        client = Client("https://api.mainnet-beta.solana.com")
        result = client.send_transaction(transaction)
        print(f"Transaction signature: {result.value}")
        """)
        
    except FileNotFoundError:
        print("❌ Wallet file not found. Create a wallet at wallets/wallet1.json")
    except ValueError as e:
        print(f"❌ Error creating swap: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def example_sell_token():
    """
    Example: Sell USDC for SOL using Jupiter aggregator
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 2: SELL TOKEN (USDC → SOL)")
    print("=" * 80)
    
    try:
        keypair = load_keypair_from_json("wallets/wallet1.json")
        print(f"✅ Wallet loaded: {keypair.pubkey()}\n")
        
        # USDC mint address
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # Create swap transaction to sell 1 USDC for SOL
        # Note: Amount is in the smallest unit (6 decimals for USDC)
        # So 1 USDC = 1,000,000 in smallest units
        # But our function expects whole units, so we pass 1.0
        transaction = create_swap_transaction(
            keypair=keypair,
            action="sell",
            token_mint_address=usdc_mint,
            amount=1.0,  # Sell 1 USDC (will be converted to lamports)
            rpc_endpoint="https://api.mainnet-beta.solana.com",
            slippage_percent=0.5,  # 0.5% slippage
            display_price_info=True
        )
        
        print("\n✅ Transaction created and signed!")
        print("⚠️  Ready to send to the network")
        
    except FileNotFoundError:
        print("❌ Wallet file not found")
    except ValueError as e:
        print(f"❌ Error: {e}")


def example_price_check_only():
    """
    Example: Just check prices without creating a swap
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 3: PRICE CHECK ONLY (CoinGecko)")
    print("=" * 80)
    
    # Get SOL price
    sol_price = get_sol_price()
    if sol_price:
        print(f"💰 Current SOL price: ${sol_price:.2f}")
    
    # Check USDC price
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    usdc_info = get_token_price_by_contract(usdc_mint)
    
    if usdc_info:
        print(f"\n🪙 {usdc_info['name']} ({usdc_info['symbol']})")
        print(f"   Price: ${usdc_info['price']:.4f}")
        print(f"   24h Change: {usdc_info['24h_change']:.2f}%")
        print(f"   Market Cap: ${usdc_info['market_cap']:,.0f}")
    
    # Check another token - Raydium (RAY)
    ray_mint = "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R"
    ray_info = get_token_price_by_contract(ray_mint)
    
    if ray_info:
        print(f"\n🪙 {ray_info['name']} ({ray_info['symbol']})")
        print(f"   Price: ${ray_info['price']:.4f}")
        print(f"   24h Change: {ray_info['24h_change']:.2f}%")
        print(f"   24h Volume: ${ray_info['24h_vol']:,.0f}")


def example_different_slippage():
    """
    Example: Creating swaps with different slippage tolerances
    """
    print("\n" + "=" * 80)
    print("EXAMPLE 4: CUSTOM SLIPPAGE TOLERANCE")
    print("=" * 80)
    
    try:
        keypair = load_keypair_from_json("wallets/wallet1.json")
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        # High slippage (for volatile tokens or low liquidity)
        print("\n📊 Creating swap with 3% slippage tolerance...")
        transaction = create_swap_transaction(
            keypair=keypair,
            action="buy",
            token_mint_address=usdc_mint,
            amount=0.01,
            rpc_endpoint="https://api.mainnet-beta.solana.com",
            slippage_percent=3.0,  # 3% slippage
            display_price_info=False  # Skip CoinGecko to save API calls
        )
        
        print("✅ High slippage transaction created")
        
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """
    Run all examples
    """
    print("\n" + "🚀" * 40)
    print("Jupiter + CoinGecko Integration Examples")
    print("🚀" * 40 + "\n")
    
    # Check if API key is set
    if os.environ.get("COINGECKO_PRO_API_KEY"):
        print("✅ CoinGecko Pro API key detected")
    else:
        print("ℹ️  Using CoinGecko free tier (rate limits apply)")
        print("   Set COINGECKO_PRO_API_KEY environment variable for Pro features\n")
    
    # Run examples
    # NOTE: Comment out examples you don't want to run
    
    example_price_check_only()
    
    # Uncomment to test actual swaps (but don't send!)
    # example_buy_token()
    # example_sell_token()
    # example_different_slippage()
    
    print("\n" + "=" * 80)
    print("✅ Examples completed!")
    print("=" * 80)
    print("\n📝 Notes:")
    print("  - Jupiter automatically finds the best route across all DEXes")
    print("  - CoinGecko provides price validation and market data")
    print("  - Transactions are signed but not sent by default")
    print("  - Always test with small amounts first!")
    print("  - Check slippage and price impact before sending")


if __name__ == "__main__":
    main()

