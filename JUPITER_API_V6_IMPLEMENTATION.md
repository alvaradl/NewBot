# Jupiter API Implementation Guide

## Overview

This implementation uses **Jupiter API**, the official aggregator API for Solana swaps. Jupiter finds the best swap routes across 20+ DEXes including Raydium, Orca, Serum, Lifinity, and more.

**Official Documentation**: https://station.jup.ag/docs/apis/swap-api

## Architecture

### Two-Step Process

Jupiter API uses a simple two-step process:

1. **GET /quote** - Get the best swap route and price
2. **POST /swap** - Build the transaction based on the quote

```
User Request
    ↓
┌─────────────────────────────────────┐
│  Step 1: Get Quote                  │
│  GET /quote                          │
│  - Finds best route across DEXes    │
│  - Returns price and route info     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  Step 2: Build Transaction          │
│  POST /swap                          │
│  - Builds serialized transaction    │
│  - Returns base64 encoded tx        │
└─────────────────────────────────────┘
    ↓
Sign & Send Transaction
```

## Implementation Details

### 1. Quote API (`get_jupiter_quote`)

**Endpoint**: `GET https://lite-api.jup.ag/swap/v1/quote`

**Required Parameters**:
- `inputMint` - Input token mint address
- `outputMint` - Output token mint address
- `amount` - Amount in lamports (smallest unit)
- `slippageBps` - Slippage tolerance in basis points (e.g., 50 = 0.5%)

**Optional Parameters**:
- `onlyDirectRoutes` - Only return direct routes (faster, may not be optimal)
- `maxAccounts` - Limit number of accounts (reduces tx size)

**Response**:
```json
{
  "inputMint": "So11111111111111111111111111111111111111112",
  "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  "inAmount": "100000000",
  "outAmount": "14250000",
  "priceImpactPct": "0.0234",
  "routePlan": [
    {
      "swapInfo": {
        "ammKey": "...",
        "label": "Orca",
        "inputMint": "...",
        "outputMint": "...",
        "inAmount": "100000000",
        "outAmount": "14250000",
        "feeAmount": "30000",
        "feeMint": "..."
      },
      "percent": 100
    }
  ],
  "otherAmountThreshold": "14107500"
}
```

**Key Fields**:
- `inAmount` - Actual input amount
- `outAmount` - Expected output amount (without slippage)
- `priceImpactPct` - Price impact percentage
- `routePlan` - Array of swap steps with DEX info
- `otherAmountThreshold` - Minimum output considering slippage

### 2. Swap API (`get_jupiter_swap_transaction`)

**Endpoint**: `POST https://lite-api.jup.ag/swap/v1/swap`

**Required Body**:
```json
{
  "quoteResponse": { /* full quote object */ },
  "userPublicKey": "UserWalletAddress..."
}
```

**Optional Parameters**:
- `wrapAndUnwrapSol` (boolean, default: true) - Auto wrap/unwrap SOL
- `useSharedAccounts` (boolean, default: true) - Use shared accounts to reduce tx size
- `feeAccount` (string) - Referral fee account for earning fees
- `computeUnitPriceMicroLamports` (number) - Priority fee in micro-lamports
- `prioritizationFeeLamports` (string|number) - Can be "auto" for automatic priority fee
- `asLegacyTransaction` (boolean, default: false) - Use legacy tx format
- `dynamicComputeUnitLimit` (boolean) - Automatically set compute unit limit
- `skipUserAccountsRpcCalls` (boolean) - Skip RPC calls for better performance

**Response**:
```json
{
  "swapTransaction": "base64EncodedSerializedTransaction",
  "lastValidBlockHeight": 123456789
}
```

**Key Fields**:
- `swapTransaction` - Base64-encoded serialized transaction (Versioned Transaction v0)
- `lastValidBlockHeight` - Block height after which transaction is invalid

## Best Practices

### 1. Slippage Settings

```python
# Stablecoins (low volatility)
slippage_bps = 10  # 0.1%

# Regular tokens
slippage_bps = 50  # 0.5% (default)

# Volatile tokens
slippage_bps = 100  # 1%

# Low liquidity tokens
slippage_bps = 300  # 3%
```

**Note**: 1% = 100 basis points (bps)

### 2. Priority Fees

For faster execution during network congestion:

```python
# Automatic (recommended)
get_jupiter_swap_transaction(
    quote=quote,
    user_public_key=str(keypair.pubkey()),
    # prioritizationFeeLamports="auto" is set by default
)

# Manual priority fee
get_jupiter_swap_transaction(
    quote=quote,
    user_public_key=str(keypair.pubkey()),
    compute_unit_price_micro_lamports=50000  # 0.05 SOL priority fee
)
```

### 3. Transaction Size Optimization

For complex routes that may exceed transaction limits:

```python
# Use direct routes only
quote = get_jupiter_quote(
    input_mint=input_mint,
    output_mint=output_mint,
    amount=amount,
    only_direct_routes=True  # Faster, simpler routes
)

# Limit max accounts
quote = get_jupiter_quote(
    input_mint=input_mint,
    output_mint=output_mint,
    amount=amount,
    max_accounts=20  # Reduce transaction size
)

# Use shared accounts
get_jupiter_swap_transaction(
    quote=quote,
    user_public_key=str(keypair.pubkey()),
    use_shared_accounts=True  # Default, reduces tx size
)
```

### 4. Error Handling

Common Jupiter errors and solutions:

```python
# SlippageToleranceExceeded (6001)
# → Increase slippage tolerance
slippage_bps = 100  # Try 1% instead of 0.5%

# NotEnoughAccountKeys (6008)
# → Transaction too large
only_direct_routes = True  # Use simpler routes
max_accounts = 20  # Limit complexity

# No routes found
# → Token pair may not have liquidity
# → Check if tokens are valid/listed
```

## Code Examples

### Basic Swap

```python
from wallet_utils import create_swap_transaction, load_keypair_from_json

# Load wallet
keypair = load_keypair_from_json("wallets/wallet1.json")

# Buy USDC with 0.1 SOL
tx = create_swap_transaction(
    keypair=keypair,
    action="buy",
    token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount=0.1,
    rpc_endpoint="https://api.mainnet-beta.solana.com",
    slippage_percent=0.5
)

# Send transaction
from solana.rpc.api import Client
client = Client("https://api.mainnet-beta.solana.com")
result = client.send_transaction(tx)
print(f"Signature: {result.value}")
```

### Advanced: Direct API Usage

```python
from wallet_utils import get_jupiter_quote, get_jupiter_swap_transaction
from solders.keypair import Keypair
from solders.transaction import Transaction
import base64

# Get quote
quote = get_jupiter_quote(
    input_mint="So11111111111111111111111111111111111111112",  # wSOL
    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    amount=100_000_000,  # 0.1 SOL in lamports
    slippage_bps=50,  # 0.5%
    only_direct_routes=False,
    max_accounts=None
)

if quote:
    print(f"Expected output: {quote['outAmount']} lamports")
    print(f"Price impact: {quote['priceImpactPct']}%")
    
    # Build transaction
    keypair = load_keypair_from_json("wallets/wallet1.json")
    
    swap_response = get_jupiter_swap_transaction(
        quote=quote,
        user_public_key=str(keypair.pubkey()),
        wrap_unwrap_sol=True,
        use_shared_accounts=True,
        compute_unit_price_micro_lamports=None  # Use auto priority fee
    )
    
    if swap_response:
        # Deserialize transaction
        tx_base64 = swap_response["swapTransaction"]
        tx_bytes = base64.b64decode(tx_base64)
        transaction = Transaction.from_bytes(tx_bytes)
        
        # Sign and send
        transaction.sign([keypair])
        from solana.rpc.api import Client
        client = Client("https://api.mainnet-beta.solana.com")
        result = client.send_transaction(transaction)
        print(f"Swap complete: {result.value}")
```

### With Referral Fees

```python
# Earn referral fees on swaps
FEE_ACCOUNT = "YourFeeAccountPublicKey..."

swap_response = get_jupiter_swap_transaction(
    quote=quote,
    user_public_key=str(keypair.pubkey()),
    wrap_unwrap_sol=True,
    fee_account=FEE_ACCOUNT  # Your fee account
)

# Jupiter will route a small percentage of fees to your account
```

## Transaction Format

### Versioned Transaction (v0)

By default, Jupiter returns **Versioned Transactions (v0)**, which:
- Support lookup tables for reduced transaction size
- Allow more complex routes
- Are the recommended format for Solana transactions

```python
# Default: Versioned Transaction v0
swap_response = get_jupiter_swap_transaction(
    quote=quote,
    user_public_key=str(keypair.pubkey()),
    as_legacy_transaction=False  # Default
)
```

### Legacy Transaction

For compatibility with older systems:

```python
# Legacy transaction format
swap_response = get_jupiter_swap_transaction(
    quote=quote,
    user_public_key=str(keypair.pubkey()),
    as_legacy_transaction=True
)
```

**Note**: Legacy transactions have more size limitations.

## API Limits

### Rate Limits

Jupiter API is **free and public** with generous rate limits:
- No API key required
- ~600 requests per minute
- No cost per transaction

### Transaction Limits

Solana transaction limits:
- Max 1232 bytes per transaction
- Max 64 accounts per transaction (legacy)
- Versioned transactions can use lookup tables for more accounts

## Monitoring & Debugging

### Check Quote Details

```python
quote = get_jupiter_quote(...)

if quote:
    print(f"Input: {quote['inAmount']} lamports")
    print(f"Output: {quote['outAmount']} lamports")
    print(f"Price Impact: {quote['priceImpactPct']}%")
    print(f"Min Output (with slippage): {quote['otherAmountThreshold']} lamports")
    
    # Route information
    for step in quote.get('routePlan', []):
        swap_info = step.get('swapInfo', {})
        print(f"DEX: {swap_info.get('label', 'Unknown')}")
        print(f"  In: {swap_info.get('inAmount')} lamports")
        print(f"  Out: {swap_info.get('outAmount')} lamports")
        print(f"  Fee: {swap_info.get('feeAmount')} lamports")
```

### Transaction Simulation

Before sending, you can simulate:

```python
from solana.rpc.api import Client

client = Client("https://api.mainnet-beta.solana.com")

# Simulate transaction
result = client.simulate_transaction(transaction)

if result.value.err:
    print(f"Simulation failed: {result.value.err}")
else:
    print("Simulation successful!")
    print(f"Logs: {result.value.logs}")
```

## Comparison with Other Approaches

### Jupiter API vs Jupiter SDK

| Feature | Jupiter API (Our Implementation) | Jupiter SDK |
|---------|----------------------------------|-------------|
| Dependencies | Minimal (requests + solana) | Heavy (TypeScript SDK) |
| Control | Full control over requests | SDK abstractions |
| Updates | Manual updates | npm updates |
| Documentation | Official API docs | SDK docs |
| Best For | Python projects, learning | JavaScript/TypeScript |

### Why API Over SDK?

1. **Simpler**: Just HTTP requests, no complex SDK
2. **Transparent**: You see exactly what's happening
3. **Python Native**: No Node.js bridge needed
4. **Up-to-date**: API changes less than SDKs
5. **Lightweight**: Fewer dependencies

## Troubleshooting

### "No routes found"

**Causes**:
- Token pair has no liquidity
- Invalid mint addresses
- Token not supported by any DEX

**Solutions**:
- Verify mint addresses are correct
- Check token exists on Solana
- Try different token pairs

### "Slippage tolerance exceeded"

**Causes**:
- Price moved too much between quote and execution
- Slippage set too low

**Solutions**:
```python
# Increase slippage
slippage_percent = 1.0  # Try 1% instead of 0.5%
```

### "Transaction too large"

**Causes**:
- Complex multi-hop route
- Too many accounts

**Solutions**:
```python
# Use direct routes
quote = get_jupiter_quote(..., only_direct_routes=True)

# Limit accounts
quote = get_jupiter_quote(..., max_accounts=20)

# Use shared accounts
get_jupiter_swap_transaction(..., use_shared_accounts=True)
```

## Updates & Versioning

**Current Version**: Jupiter API

Jupiter API is stable and well-documented. Changes are rare and announced well in advance.

**Stay Updated**:
- Official Docs: https://station.jup.ag/docs/apis/swap-api
- Twitter: @JupiterExchange
- Discord: Official Jupiter Discord

## Security Considerations

### ✅ Safe Practices

1. **Always simulate transactions** before sending
2. **Start with small amounts** when testing
3. **Verify token addresses** from official sources
4. **Check price impact** before confirming swaps
5. **Use appropriate slippage** for token volatility

### ⚠️ Warning Signs

- Price impact > 5% (very large trade or low liquidity)
- Unverified token addresses
- Extremely high slippage requirements (>10%)
- Tokens with no CoinGecko listing

## Summary

This implementation provides:
- ✅ **Full Jupiter API compliance**
- ✅ **Proper error handling** with specific error codes
- ✅ **Versioned Transaction (v0)** support
- ✅ **Auto priority fees** for faster execution
- ✅ **Shared accounts** for transaction size optimization
- ✅ **Detailed documentation** and examples
- ✅ **Best practices** built-in

You're now ready to perform production-quality swaps on Solana using Jupiter! 🚀

---

**Questions?** Check the official Jupiter documentation:
- API Guide: https://station.jup.ag/docs/apis/swap-api
- Quote API: https://station.jup.ag/docs/apis/swap-api
- Swap API: https://station.jup.ag/docs/apis/swap-api

