# Jupiter + CoinGecko Integration Guide

## Overview

This project provides a complete Solana token swap solution by combining two powerful APIs:

1. **Jupiter Aggregator** - The leading DEX aggregator on Solana
   - Finds the best swap routes across 20+ DEXes (Raydium, Orca, Serum, etc.)
   - Provides optimal pricing and liquidity
   - Handles all transaction building

2. **CoinGecko API** - Cryptocurrency market data platform
   - Provides real-time token prices
   - Market cap, volume, and trend data
   - Price validation before swaps

## Why This Combination?

### CoinGecko is NOT a DEX

**Important:** CoinGecko does **not** provide DEX functionality. It's a data aggregation platform that:
- ✅ Tracks cryptocurrency prices
- ✅ Provides market statistics
- ✅ Shows historical data
- ❌ Cannot execute swaps
- ❌ Does not access liquidity pools
- ❌ Cannot build transactions

### Jupiter is the DEX Aggregator

Jupiter handles the actual swap execution:
- ✅ Aggregates liquidity from 20+ Solana DEXes
- ✅ Finds the best swap route
- ✅ Builds complete swap transactions
- ✅ Handles slippage protection
- ✅ Optimizes for best price

### Better Together

By combining both:
1. **CoinGecko** validates prices and shows market context
2. **Jupiter** executes the actual swap with best routing
3. You get both **market intelligence** and **execution power**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   create_swap_transaction()                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ├──► Step 0: CoinGecko Price Check
                          │    ├─ get_sol_price()
                          │    └─ get_token_price_by_contract()
                          │
                          ├──► Step 1: Determine Swap Direction
                          │    └─ Buy (SOL → Token) or Sell (Token → SOL)
                          │
                          ├──► Step 2: Jupiter Quote
                          │    ├─ get_jupiter_quote()
                          │    ├─ Finds best route across DEXes
                          │    └─ Returns price impact & output amount
                          │
                          ├──► Step 3: Build Transaction
                          │    ├─ get_jupiter_swap_transaction()
                          │    └─ Returns signed, ready-to-send transaction
                          │
                          └──► Step 4: Sign & Return
                               └─ Transaction ready for client.send_transaction()
```

## Features

### 🔄 Complete Swap Implementation

The `create_swap_transaction()` function provides:

- **Price Discovery**: CoinGecko shows you current market prices
- **Route Optimization**: Jupiter finds the best path across multiple DEXes
- **Slippage Protection**: Configure acceptable price movement
- **Price Impact Display**: See how your trade affects the market
- **Market Context**: 24h volume, price changes, market cap

### 💰 Price Validation (CoinGecko)

Before executing swaps, get comprehensive market data:

```python
from wallet_utils import get_token_price_by_contract

# Get detailed token information
token_info = get_token_price_by_contract(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
)

if token_info:
    print(f"Price: ${token_info['price']}")
    print(f"24h Change: {token_info['24h_change']}%")
    print(f"Market Cap: ${token_info['market_cap']:,}")
```

### 🚀 Swap Execution (Jupiter)

Execute swaps with best pricing:

```python
from wallet_utils import load_keypair_from_json, create_swap_transaction

keypair = load_keypair_from_json("wallets/wallet1.json")

# Buy USDC with 0.1 SOL
tx = create_swap_transaction(
    keypair=keypair,
    action="buy",
    token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    amount=0.1,
    rpc_endpoint="https://api.mainnet-beta.solana.com",
    slippage_percent=1.0
)

# Transaction is signed and ready to send
from solana.rpc.api import Client
client = Client("https://api.mainnet-beta.solana.com")
signature = client.send_transaction(tx)
print(f"Swap executed: {signature.value}")
```

## Setup & Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `coingecko_sdk` - CoinGecko API client
- `requests` - HTTP requests for Jupiter API
- `solana` - Solana Python SDK
- `solders` - Solana transaction library
- `base58` - Base58 encoding

### 2. Configure CoinGecko API (Optional)

For better rate limits, set up a Demo API key:

```bash
# Windows PowerShell
$env:COINGECKO_DEMO_API_KEY="CG-your-api-key-here"

# Linux/Mac
export COINGECKO_DEMO_API_KEY="CG-your-api-key-here"
```

**Free tier works fine** for most use cases (10-50 calls/minute).

### 3. No Jupiter API Key Needed

Jupiter's public API requires **no authentication** - it's completely free!

## API Reference

### Main Swap Function

#### `create_swap_transaction()`

Creates a complete swap transaction using Jupiter, with CoinGecko price validation.

**Parameters:**
- `keypair` (Keypair): Your wallet keypair
- `action` ("buy" | "sell"): Swap direction
  - `"buy"`: Trade SOL for token
  - `"sell"`: Trade token for SOL
- `token_mint_address` (str): Token contract address
- `amount` (float): Amount to swap (in whole units, not lamports)
- `rpc_endpoint` (str): Solana RPC endpoint
- `slippage_percent` (float, default=1.0): Max acceptable slippage
- `display_price_info` (bool, default=True): Show CoinGecko prices

**Returns:**
- `Transaction`: Signed transaction ready to send

**Raises:**
- `ValueError`: If quote fails or transaction building fails

### Helper Functions

#### `get_jupiter_quote()`

Get swap quote from Jupiter aggregator.

**Parameters:**
- `input_mint` (str): Input token mint address
- `output_mint` (str): Output token mint address
- `amount` (int): Amount in lamports
- `slippage_bps` (int): Slippage in basis points (100 = 1%)

**Returns:**
- `Dict`: Quote data with route and pricing info

#### `get_jupiter_swap_transaction()`

Build swap transaction from Jupiter quote.

**Parameters:**
- `quote` (Dict): Quote from `get_jupiter_quote()`
- `user_public_key` (str): Wallet public key
- `wrap_unwrap_sol` (bool): Auto wrap/unwrap SOL

**Returns:**
- `str`: Base64-encoded transaction

#### `get_sol_price()`

Get current SOL price from CoinGecko.

**Returns:**
- `float`: SOL price in USD (or None on error)

#### `get_token_price_by_contract()`

Get token info from CoinGecko by contract address.

**Parameters:**
- `contract_address` (str): Token mint address
- `platform` (str, default="solana"): Blockchain platform
- `vs_currency` (str, default="usd"): Currency for price

**Returns:**
- `Dict`: Token info including price, volume, market cap

## Example Usage

### Basic Swap

```python
from wallet_utils import load_keypair_from_json, create_swap_transaction

# Load wallet
keypair = load_keypair_from_json("wallets/wallet1.json")

# Buy 0.05 SOL worth of USDC
tx = create_swap_transaction(
    keypair=keypair,
    action="buy",
    token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    amount=0.05,
    rpc_endpoint="https://api.mainnet-beta.solana.com"
)

# Send transaction
from solana.rpc.api import Client
client = Client("https://api.mainnet-beta.solana.com")
result = client.send_transaction(tx)
print(f"Success! Signature: {result.value}")
```

### Price Check Before Swap

```python
from wallet_utils import get_sol_price, get_token_price_by_contract

# Check current prices
sol_price = get_sol_price()
usdc_info = get_token_price_by_contract("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

print(f"SOL: ${sol_price:.2f}")
print(f"USDC: ${usdc_info['price']:.4f}")
print(f"24h change: {usdc_info['24h_change']:.2f}%")

# Now execute swap with confidence
```

### Custom Slippage for Volatile Tokens

```python
# For volatile or low-liquidity tokens, use higher slippage
tx = create_swap_transaction(
    keypair=keypair,
    action="buy",
    token_mint_address="VolatileTokenMintAddress",
    amount=0.1,
    rpc_endpoint="https://api.mainnet-beta.solana.com",
    slippage_percent=5.0  # 5% slippage for volatile token
)
```

## Common Token Addresses

```python
# Stablecoins
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

# Wrapped SOL
WSOL = "So11111111111111111111111111111111111111112"

# Popular tokens
RAY = "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R"  # Raydium
ORCA = "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"  # Orca
```

## Best Practices

### 1. Always Test with Small Amounts
```python
# Start with tiny amounts to test
amount = 0.001  # 0.001 SOL for testing
```

### 2. Check Price Impact
```python
# The function displays price impact from Jupiter
# High impact (>1%) means your trade significantly affects the market
# Consider splitting large trades
```

### 3. Set Appropriate Slippage
```python
# Stablecoins: 0.1-0.5%
slippage_percent = 0.5

# Regular tokens: 1-2%
slippage_percent = 1.0

# Volatile/Low liquidity: 3-5%
slippage_percent = 3.0
```

### 4. Use Price Validation
```python
# Always check CoinGecko prices first
token_info = get_token_price_by_contract(mint_address)
if not token_info:
    print("⚠️ Token not found on CoinGecko - may be risky")
```

### 5. Handle Errors Gracefully
```python
try:
    tx = create_swap_transaction(...)
    result = client.send_transaction(tx)
except ValueError as e:
    print(f"Swap failed: {e}")
    # Handle error appropriately
```

## Limitations & Known Issues

### CoinGecko Limitations
- Not all Solana tokens are listed
- Free tier has rate limits (10-50 calls/min)
- Prices may have slight delays

### Jupiter Limitations
- Requires sufficient liquidity in pools
- Very new tokens may not be available
- Price impact can be high for large trades

### Transaction Fees
- Solana network fees (~0.000005 SOL per transaction)
- Jupiter may include priority fees for faster execution
- No additional Jupiter API fees

## Troubleshooting

### "Failed to get quote from Jupiter"
- Token pair may not have liquidity
- Amount too large for available liquidity
- Try reducing amount or checking different tokens

### "Token not found on CoinGecko"
- Very new or unlisted tokens won't appear
- Disable `display_price_info=False` to skip CoinGecko
- Proceed with caution - unverified tokens

### "Transaction failed to send"
- Check wallet has sufficient SOL for the trade + fees
- Verify RPC endpoint is working
- May need higher slippage for volatile markets

## Additional Resources

- [Jupiter Documentation](https://station.jup.ag/docs)
- [CoinGecko API Docs](https://docs.coingecko.com/)
- [Solana Web3.py Docs](https://michaelhly.github.io/solana-py/)

## Support & Contributing

For issues or questions:
1. Check this documentation first
2. Review example files (`example_jupiter_swap.py`)
3. Check API status (Jupiter, CoinGecko, Solana RPC)

## License

This code is provided as-is for educational purposes. Always test thoroughly before using with real funds.

