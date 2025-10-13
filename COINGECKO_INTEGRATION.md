# CoinGecko SDK Integration

This document explains the CoinGecko SDK integration added to the wallet utilities.

## Overview

The `wallet_utils.py` module now includes CoinGecko API integration to fetch real-time cryptocurrency prices and market data. This enhances the swap transaction functionality by providing price information before executing trades.

## Features Added

### 1. Client Initialization (`get_coingecko_client()`)

Creates a reusable CoinGecko API client with automatic retry handling.

- **Demo API Support**: Automatically uses Demo API if `COINGECKO_DEMO_API_KEY` environment variable is set
- **Free Tier Fallback**: Falls back to free tier if no API key is provided
- **Automatic Retries**: Configured with `max_retries=3` for reliability

### 2. Token Price Lookup (`get_token_price_by_contract()`)

Fetches comprehensive market data for a token by its contract address.

**Returns:**
- Token name and symbol
- Current price (in USD or specified currency)
- Market capitalization
- 24-hour trading volume
- 24-hour price change percentage

**Example:**
```python
from wallet_utils import get_token_price_by_contract

# Get USDC price data
price_data = get_token_price_by_contract(
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC on Solana
    platform="solana",
    vs_currency="usd"
)

if price_data:
    print(f"Token: {price_data['name']} ({price_data['symbol']})")
    print(f"Price: ${price_data['price']:.2f}")
    print(f"24h Change: {price_data['24h_change']:.2f}%")
```

### 3. SOL Price Lookup (`get_sol_price()`)

Quick function to get the current SOL price.

**Example:**
```python
from wallet_utils import get_sol_price

sol_price = get_sol_price()
if sol_price:
    print(f"1 SOL = ${sol_price:.2f}")
```

### 4. Enhanced Swap Transaction (`create_swap_transaction()`)

The swap transaction function now includes:

- **Automatic Price Fetching**: Gets real-time prices for both SOL and the target token
- **Trade Estimates**: Calculates expected output amounts based on current prices
- **Market Information**: Displays relevant market data to help make informed decisions
- **Slippage Configuration**: Added `slippage_percent` parameter
- **Optional Price Display**: Can disable price fetching with `display_price_info=False`

**New Parameters:**
- `slippage_percent` (float): Maximum acceptable slippage percentage (default: 1.0%)
- `display_price_info` (bool): Whether to fetch and display CoinGecko prices (default: True)

**Example:**
```python
from wallet_utils import load_keypair_from_json, create_swap_transaction

keypair = load_keypair_from_json("wallets/wallet1.json")

tx = create_swap_transaction(
    keypair=keypair,
    action="buy",
    token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount=0.5,  # 0.5 SOL
    rpc_endpoint="https://api.mainnet-beta.solana.com",
    slippage_percent=1.5,  # 1.5% slippage tolerance
    display_price_info=True  # Show CoinGecko price data
)
```

## Error Handling

All CoinGecko functions implement proper error handling:

- **`RateLimitError`**: Catches rate limit errors and displays a user-friendly message
- **`APIError`**: Catches general API errors with detailed error information
- **Generic Exception**: Catches unexpected errors to prevent crashes

All functions return `None` on error, allowing the caller to handle failures gracefully.

## Setup

### Using Free Tier (No API Key)

The integration works out of the box with CoinGecko's free tier:

```bash
pip install coingecko_sdk
python example_usage.py
```

**Free Tier Limitations:**
- 10-50 calls per minute
- Basic endpoints only
- Public data only

### Using Demo API (Recommended)

For better rate limits and additional features:

1. Get an API key from [CoinGecko](https://www.coingecko.com/en/api/pricing)

2. Set the environment variable:
   ```bash
   # Windows PowerShell
   $env:COINGECKO_DEMO_API_KEY="CG-your-api-key-here"
   
   # Linux/Mac
   export COINGECKO_DEMO_API_KEY="CG-your-api-key-here"
   ```

3. Or use a `.env` file:
   ```
   COINGECKO_DEMO_API_KEY=CG-your-api-key-here
   ```

**Demo Tier Benefits:**
- Higher rate limits (500+ calls per minute)
- Access to Demo endpoints
- Better reliability
- Priority support

## Best Practices

1. **Cache Prices**: For frequent calls, consider caching prices to reduce API calls
2. **Handle Errors**: Always check if the returned value is `None` before using it
3. **Rate Limits**: Be mindful of rate limits, especially on free tier
4. **Token Availability**: Not all Solana tokens are listed on CoinGecko

## Example Output

When running a swap transaction with price info enabled:

```
======================================================================
🔄 Preparing to BUY transaction
======================================================================
Wallet: 7xYz...
Token: EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
Amount: 0.5 SOL
Slippage tolerance: 1.5%

======================================================================
📊 Fetching market data from CoinGecko...
======================================================================
💰 SOL Price: $142.50

🪙 Token: USD Coin (USDC)
   Price: $1.00000000
   Market Cap: $35,000,000,000
   24h Volume: $8,500,000,000
   24h Change: -0.02%

📈 Estimated output: ~71.25 USDC
   (Based on current CoinGecko prices)
```

## Next Steps

The swap transaction function is still a skeleton. To complete it, you need to:

1. **Integrate with a DEX**: Choose a DEX SDK (Raydium, Orca, Jupiter, etc.)
2. **Find Liquidity Pools**: Implement pool discovery for token pairs
3. **Build Swap Instructions**: Create the actual swap transaction instructions
4. **Handle Slippage**: Implement slippage calculations in the swap instruction

The CoinGecko integration provides the market data foundation for making informed trading decisions.

## Files

- `wallet_utils.py` - Main utilities with CoinGecko integration
- `example_usage.py` - Example code demonstrating the features
- `requirements.txt` - Updated with `coingecko_sdk` dependency

## Support

For CoinGecko API documentation, visit:
- [CoinGecko API Documentation](https://docs.coingecko.com/reference/introduction)
- [CoinGecko SDK GitHub](https://github.com/coingecko/coingecko-sdk-python)

