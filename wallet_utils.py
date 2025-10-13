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
from typing import List, Tuple, Literal, Optional, Dict
import base64

import requests
from solders.keypair import Keypair
from solders.transaction import Transaction, VersionedTransaction
from coingecko_sdk import Coingecko, RateLimitError, APIError


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


def get_coingecko_client() -> Coingecko:
    """
    Initialize and return a CoinGecko API client.
    
    This function creates a reusable CoinGecko client instance with automatic
    retries enabled. It loads the API key from the COINGECKO_DEMO_API_KEY
    environment variable if available.
    
    Returns:
        Coingecko: An initialized CoinGecko client instance.
        
    Example:
        client = get_coingecko_client()
        price_data = client.simple.price.get(ids="bitcoin", vs_currencies="usd")
    """
    api_key = os.environ.get("COINGECKO_DEMO_API_KEY")
    
    if api_key:
        # Initialize demo tier client with API key
        client = Coingecko(
            demo_api_key=api_key,
            environment="demo",
            max_retries=3,
        )
    else:
        # Initialize free tier client (without API key)
        client = Coingecko(max_retries=3)
    
    return client


def get_token_price_by_contract(
    contract_address: str,
    platform: str = "solana",
    vs_currency: str = "usd"
) -> Optional[Dict]:
    """
    Get the current price and market data for a token by its contract address.
    
    Args:
        contract_address: The token's contract/mint address.
        platform: The blockchain platform (default: "solana").
        vs_currency: The currency to get the price in (default: "usd").
    
    Returns:
        Optional[Dict]: A dictionary containing price and market data, or None if the token
                       is not found or an error occurs. The dictionary includes:
                       - 'price': Current price in the specified currency
                       - 'market_cap': Market capitalization
                       - '24h_vol': 24-hour trading volume
                       - '24h_change': 24-hour price change percentage
    
    Example:
        # Get price for a Solana token
        price_data = get_token_price_by_contract(
            "So11111111111111111111111111111111111111112"  # Wrapped SOL
        )
        if price_data:
            print(f"Current price: ${price_data['price']}")
    """
    client = get_coingecko_client()
    
    try:
        # Get token data by contract address
        # Note: The SDK's contract.get() only accepts id and contract_address
        # It returns all data by default, and we extract what we need
        response = client.coins.contract.get(
            id=platform,
            contract_address=contract_address
        )
        
        if response and hasattr(response, 'market_data') and response.market_data:
            market_data = response.market_data
            
            # Extract relevant price information (CoinGecko SDK returns Pydantic models)
            price_info = {
                'price': getattr(market_data.current_price, vs_currency, 0) if market_data.current_price else 0,
                'market_cap': getattr(market_data.market_cap, vs_currency, 0) if market_data.market_cap else 0,
                '24h_vol': getattr(market_data.total_volume, vs_currency, 0) if market_data.total_volume else 0,
                '24h_change': market_data.price_change_percentage_24h or 0,
                'name': response.name if hasattr(response, 'name') else 'Unknown',
                'symbol': response.symbol.upper() if hasattr(response, 'symbol') else 'UNKNOWN'
            }
            
            return price_info
        
        return None
        
    except RateLimitError:
        print("⚠️ CoinGecko rate limit exceeded. Please try again later.")
        return None
    except APIError as e:
        print(f"⚠️ CoinGecko API error: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Error fetching token price: {e}")
        return None


def get_sol_price(vs_currency: str = "usd") -> Optional[float]:
    """
    Get the current price of Solana (SOL).
    
    Args:
        vs_currency: The currency to get the price in (default: "usd").
    
    Returns:
        Optional[float]: The current SOL price, or None if an error occurs.
    
    Example:
        sol_price = get_sol_price()
        if sol_price:
            print(f"1 SOL = ${sol_price}")
    """
    client = get_coingecko_client()
    
    try:
        price_data = client.simple.price.get(
            ids="solana",
            vs_currencies=vs_currency,
        )
        
        # CoinGecko SDK returns Pydantic models, access via attributes
        if price_data and hasattr(price_data, 'solana'):
            solana_price = getattr(price_data.solana, vs_currency, None)
            return float(solana_price) if solana_price else None
        
        return None
        
    except RateLimitError:
        print("⚠️ CoinGecko rate limit exceeded. Please try again later.")
        return None
    except APIError as e:
        print(f"⚠️ CoinGecko API error: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Error fetching SOL price: {e}")
        return None


# Jupiter DEX Aggregator Constants
# Official Jupiter API endpoint
JUPITER_API_BASE = "https://lite-api.jup.ag/swap/v1"
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"  # wSOL


def get_jupiter_quote(
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: int = 50,
    only_direct_routes: bool = False,
    max_accounts: Optional[int] = None
) -> Optional[Dict]:
    """
    Get a swap quote from Jupiter aggregator API.
    
    Jupiter aggregates liquidity from multiple DEXes on Solana to find
    the best swap route. This uses the official Jupiter Quote API.
    
    Reference: https://station.jup.ag/docs/apis/swap-api
    
    Args:
        input_mint: The mint address of the input token.
        output_mint: The mint address of the output token.
        amount: The amount to swap in lamports (smallest unit).
                For SOL: 1 SOL = 1,000,000,000 lamports
                For SPL tokens: amount depends on token decimals (e.g., USDC has 6 decimals)
        slippage_bps: Slippage tolerance in basis points (50 bps = 0.5%).
                     Default is 50 bps. Max is typically 1000 bps (10%).
        only_direct_routes: If true, only returns direct routes (default: False).
                           Direct routes may have better price but limited options.
        max_accounts: Maximum number of accounts to use in the route (optional).
                     Useful for reducing transaction size.
    
    Returns:
        Optional[Dict]: Quote data from Jupiter API containing:
                       - inAmount: Input amount in lamports
                       - outAmount: Expected output amount in lamports
                       - priceImpactPct: Price impact percentage
                       - routePlan: Array of route steps with DEX info
                       - otherAmountThreshold: Minimum output considering slippage
                       Returns None if an error occurs.
    
    Example:
        # Get quote for swapping 1 SOL to USDC
        quote = get_jupiter_quote(
            input_mint="So11111111111111111111111111111111111111112",  # wSOL
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount=1_000_000_000,  # 1 SOL in lamports
            slippage_bps=50  # 0.5% slippage
        )
        if quote:
            print(f"Expected output: {quote['outAmount']} lamports")
            print(f"Price impact: {quote['priceImpactPct']}%")
    """
    try:
        # Build query parameters according to Jupiter API spec
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps)
        }
        
        # Add optional parameters if specified
        if only_direct_routes:
            params["onlyDirectRoutes"] = "true"
        
        if max_accounts is not None:
            params["maxAccounts"] = str(max_accounts)
        
        # Call Jupiter Quote API
        response = requests.get(
            f"{JUPITER_API_BASE}/quote",
            params=params,
            timeout=15,  # Increased timeout for complex routes
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            quote_data = response.json()
            
            # Validate response has required fields
            if "outAmount" not in quote_data:
                print("⚠️ Jupiter quote response missing required fields")
                return None
            
            return quote_data
        elif response.status_code == 400:
            print("⚠️ Jupiter quote error: Invalid request parameters")
            print(f"   Details: {response.text}")
            return None
        elif response.status_code == 404:
            print("⚠️ Jupiter quote error: No routes found for this token pair")
            return None
        else:
            print(f"⚠️ Jupiter quote error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("⚠️ Jupiter API request timed out (network may be slow)")
        return None
    except requests.exceptions.ConnectionError:
        print("⚠️ Failed to connect to Jupiter API (check internet connection)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Jupiter API request error: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error getting Jupiter quote: {e}")
        return None


def get_jupiter_swap_transaction(
    quote: Dict,
    user_public_key: str,
    wrap_unwrap_sol: bool = True,
    use_shared_accounts: bool = True,
    fee_account: Optional[str] = None,
    compute_unit_price_micro_lamports: Optional[int] = None,
    as_legacy_transaction: bool = False
) -> Optional[Dict]:
    """
    Get a serialized swap transaction from Jupiter Swap API.
    
    This function calls the Jupiter Swap API to build a complete transaction
    that can be signed and sent to the Solana network.
    
    Reference: https://station.jup.ag/docs/apis/swap-api
    
    Args:
        quote: The full quote response object from get_jupiter_quote().
        user_public_key: The user's wallet public key as a base58 string.
        wrap_unwrap_sol: Whether to automatically wrap/unwrap SOL (default: True).
                        If false, user must have wSOL account.
        use_shared_accounts: Use shared program accounts (default: True).
                            This can reduce transaction size.
        fee_account: Optional referral fee account public key for earning fees.
        compute_unit_price_micro_lamports: Optional priority fee in micro-lamports.
                                          If None, uses "auto" for automatic priority fee.
        as_legacy_transaction: If true, use legacy transaction format (default: False).
                              False uses Versioned Transaction (v0) which is recommended.
    
    Returns:
        Optional[Dict]: Response from Jupiter containing:
                       - swapTransaction: Base64-encoded serialized transaction
                       - lastValidBlockHeight: Last valid block height for the transaction
                       Returns None if an error occurs.
    
    Raises:
        None - Returns None on error with printed error messages.
    
    Example:
        quote = get_jupiter_quote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1_000_000_000
        )
        
        if quote:
            swap_data = get_jupiter_swap_transaction(
                quote=quote,
                user_public_key=str(keypair.pubkey()),
                wrap_unwrap_sol=True
            )
            
            if swap_data:
                tx_base64 = swap_data["swapTransaction"]
                # Deserialize and sign the transaction
    """
    try:
        # Build request body according to Jupiter Swap API spec
        request_data = {
            "quoteResponse": quote,
            "userPublicKey": user_public_key,
            "wrapAndUnwrapSol": wrap_unwrap_sol,
            "useSharedAccounts": use_shared_accounts,
            "dynamicComputeUnitLimit": True,  # Automatically set compute unit limit
            "skipUserAccountsRpcCalls": True  # Skip RPC calls for better performance
        }
        
        # Add optional priority fee
        if compute_unit_price_micro_lamports is not None:
            request_data["computeUnitPriceMicroLamports"] = compute_unit_price_micro_lamports
        else:
            # Use "auto" for automatic priority fee calculation
            request_data["prioritizationFeeLamports"] = "auto"
        
        # Add optional referral fee account
        if fee_account:
            request_data["feeAccount"] = fee_account
        
        # Set transaction format
        if as_legacy_transaction:
            request_data["asLegacyTransaction"] = True
        
        # Call Jupiter Swap API
        response = requests.post(
            f"{JUPITER_API_BASE}/swap",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            swap_data = response.json()
            
            # Validate response has required fields
            if "swapTransaction" not in swap_data:
                print("⚠️ Jupiter swap response missing swapTransaction field")
                return None
            
            return swap_data
        elif response.status_code == 400:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", response.text)
            print("⚠️ Jupiter swap error: Invalid request")
            print(f"   Details: {error_msg}")
            
            # Check for specific error codes from Jupiter
            if "SlippageToleranceExceeded" in str(error_msg):
                print("   💡 Tip: Try increasing slippage tolerance")
            elif "NotEnoughAccountKeys" in str(error_msg):
                print("   💡 Tip: Transaction too large, try direct routes or reduce complexity")
            
            return None
        elif response.status_code == 404:
            print("⚠️ Jupiter swap error: Endpoint not found (check API version)")
            return None
        else:
            print(f"⚠️ Jupiter swap error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print("⚠️ Jupiter API request timed out (network may be slow)")
        return None
    except requests.exceptions.ConnectionError:
        print("⚠️ Failed to connect to Jupiter API (check internet connection)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Jupiter API request error: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error getting Jupiter swap transaction: {e}")
        return None


def create_swap_transaction(
    keypair: Keypair,
    action: Literal["buy", "sell"],
    token_mint_address: str,
    amount: float,
    rpc_endpoint: str,
    slippage_percent: float = 1.0,
    display_price_info: bool = True,
) -> VersionedTransaction:
    """
    Creates a fully functional buy or sell swap transaction using Jupiter aggregator.

    This function provides a complete swap implementation by integrating:
    - **CoinGecko API**: Fetches real-time token prices and market data for validation
    - **Jupiter Aggregator**: Finds the best swap route across multiple Solana DEXes
      (Raydium, Orca, Serum, etc.) and builds the swap transaction

    The function performs these steps:
    1. Fetches token prices and market data from CoinGecko (optional)
    2. Calculates swap amounts and determines input/output mints
    3. Gets the best swap quote from Jupiter aggregator
    4. Builds and signs the swap transaction
    5. Returns a ready-to-send transaction

    Args:
        keypair: The keypair of the wallet executing the swap.
        action: The action to perform, either "buy" or "sell".
                - "buy": Swap SOL for the specified token
                - "sell": Swap the specified token for SOL
        token_mint_address: The mint address of the token to trade.
        amount: The amount to swap:
                - For "buy": Amount of SOL to spend
                - For "sell": Amount of tokens to sell (in whole units)
        rpc_endpoint: The Solana RPC endpoint URL.
        slippage_percent: Maximum acceptable slippage percentage (default: 1.0%).
                         Jupiter will find the best route within this tolerance.
        display_price_info: Whether to display price information from CoinGecko (default: True).

    Returns:
        VersionedTransaction: A signed Solana versioned transaction (v0), ready to be sent to the network.

    Raises:
        ValueError: If the action is invalid, quote fails, or transaction building fails.

    Example:
        # Buy 0.1 SOL worth of USDC
        from wallet_utils import load_keypair_from_json, create_swap_transaction
        
        keypair = load_keypair_from_json("wallets/wallet1.json")
        tx = create_swap_transaction(
            keypair=keypair,
            action="buy",
            token_mint_address="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            amount=0.1,
            rpc_endpoint="https://api.mainnet-beta.solana.com",
            slippage_percent=1.5
        )
        
        # Send the transaction
        from solana.rpc.api import Client
        client = Client("https://api.mainnet-beta.solana.com")
        signature = client.send_transaction(tx)
        print(f"Transaction sent: {signature.value}")
    """
    owner = keypair.pubkey()

    print(f"\n{'='*70}")
    print(f"🔄 Preparing to {action.upper()} transaction")
    print(f"{'='*70}")
    print(f"Wallet: {owner}")
    print(f"Token: {token_mint_address}")
    print(f"Amount: {amount} {'SOL' if action == 'buy' else 'tokens'}")
    print(f"Slippage tolerance: {slippage_percent}%")

    # Step 0: Fetch price information from CoinGecko
    # -----------------------------------------------------------------
    # Get real-time price data to help with the swap decision
    if display_price_info:
        print(f"\n{'='*70}")
        print("📊 Fetching market data from CoinGecko...")
        print(f"{'='*70}")
        
        # Get SOL price
        sol_price = get_sol_price()
        if sol_price:
            print(f"💰 SOL Price: ${sol_price:.2f}")
        
        # Get token price and info
        token_info = get_token_price_by_contract(token_mint_address)
        if token_info:
            print(f"\n🪙 Token: {token_info['name']} ({token_info['symbol']})")
            print(f"   Price: ${token_info['price']:.8f}")
            print(f"   Market Cap: ${token_info['market_cap']:,.0f}")
            print(f"   24h Volume: ${token_info['24h_vol']:,.0f}")
            print(f"   24h Change: {token_info['24h_change']:.2f}%")
            
            # Calculate estimated output amount
            if action == "buy" and sol_price and token_info['price'] > 0:
                usd_value = amount * sol_price
                estimated_tokens = usd_value / token_info['price']
                print(f"\n📈 Estimated output: ~{estimated_tokens:,.2f} {token_info['symbol']}")
                print("   (Based on current CoinGecko prices)")
            elif action == "sell" and sol_price and token_info['price'] > 0:
                usd_value = amount * token_info['price']
                estimated_sol = usd_value / sol_price
                print(f"\n📉 Estimated output: ~{estimated_sol:.4f} SOL")
                print("   (Based on current CoinGecko prices)")
        else:
            print("⚠️  Could not fetch token price from CoinGecko")
            print("   (Token may not be listed or API limit reached)")

    # 1. Determine input/output mints based on buy/sell action
    # -----------------------------------------------------------------
    # Jupiter needs to know which token is the input and which is output
    print(f"\n{'='*70}")
    print("Step 1: Determining swap direction and calculating amounts")
    print(f"{'='*70}")
    
    # Convert amount to lamports (smallest unit)
    # 1 SOL = 1,000,000,000 lamports
    amount_in_lamports = int(amount * 1_000_000_000)
    
    if action == "buy":
        # Buying token with SOL
        input_mint = WRAPPED_SOL_MINT  # wSOL
        output_mint = token_mint_address
        print(f"💰 Buying {token_mint_address}")
        print(f"   Input: {amount} SOL ({amount_in_lamports:,} lamports)")
    elif action == "sell":
        # Selling token for SOL
        input_mint = token_mint_address
        output_mint = WRAPPED_SOL_MINT  # wSOL
        print(f"💰 Selling {amount} tokens of {token_mint_address}")
        print(f"   Amount: {amount_in_lamports:,} lamports")
    else:
        raise ValueError(f"Invalid action: {action}. Must be 'buy' or 'sell'")
    
    print(f"   Input mint: {input_mint}")
    print(f"   Output mint: {output_mint}")

    # 2. Get quote from Jupiter aggregator
    # -----------------------------------------------------------------
    # Jupiter finds the best route across multiple DEXes
    print(f"\n{'='*70}")
    print("Step 2: Getting swap quote from Jupiter aggregator")
    print(f"{'='*70}")
    
    # Convert slippage percentage to basis points (1% = 100 bps)
    slippage_bps = int(slippage_percent * 100)
    
    quote = get_jupiter_quote(
        input_mint=input_mint,
        output_mint=output_mint,
        amount=amount_in_lamports,
        slippage_bps=slippage_bps
    )
    
    if not quote:
        raise ValueError(
            "Failed to get quote from Jupiter. "
            "The token pair may not have sufficient liquidity or the API is unavailable."
        )
    
    # Display quote information
    in_amount = int(quote.get("inAmount", 0))
    out_amount = int(quote.get("outAmount", 0))
    price_impact = float(quote.get("priceImpactPct", 0))
    
    # Detect the DEX/route being used
    route_label = quote.get('routePlan', [{}])[0].get('swapInfo', {}).get('label', 'Unknown') if quote.get('routePlan') else 'Direct'
    
    print("✅ Quote received")
    print(f"   Input: {in_amount:,} lamports")
    print(f"   Expected output: {out_amount:,} lamports")
    print(f"   Price impact: {price_impact:.4f}%")
    print(f"   Route: {route_label}")
    
    # Detect Pump.fun or Simple AMMs - they don't support shared accounts
    is_simple_amm = "Pump.fun" in route_label or "pump" in route_label.lower()
    
    # 3. Get swap transaction from Jupiter
    # -----------------------------------------------------------------
    # Jupiter builds the complete transaction for us
    print(f"\n{'='*70}")
    print("Step 3: Building swap transaction from Jupiter")
    print(f"{'='*70}")
    
    # Disable shared accounts for Pump.fun/Simple AMMs
    use_shared_accounts = not is_simple_amm
    
    if is_simple_amm:
        print("ℹ️  Detected Pump.fun/Simple AMM - disabling shared accounts")
    
    swap_response = get_jupiter_swap_transaction(
        quote=quote,
        user_public_key=str(owner),
        wrap_unwrap_sol=True,  # Automatically wrap/unwrap SOL
        use_shared_accounts=use_shared_accounts
    )
    
    # If shared accounts fail, retry without them
    if not swap_response and use_shared_accounts:
        print("⚠️  Retrying without shared accounts (required for Pump.fun/Simple AMMs)...")
        swap_response = get_jupiter_swap_transaction(
            quote=quote,
            user_public_key=str(owner),
            wrap_unwrap_sol=True,
            use_shared_accounts=False  # Disable shared accounts
        )
    
    if not swap_response:
        raise ValueError("Failed to get swap transaction from Jupiter")
    
    # Extract the base64 transaction from the response
    swap_tx_base64 = swap_response.get("swapTransaction")
    if not swap_tx_base64:
        raise ValueError("Jupiter response missing swapTransaction field")
    
    # Display additional info from Jupiter
    last_valid_block_height = swap_response.get("lastValidBlockHeight")
    if last_valid_block_height:
        print(f"✅ Transaction valid until block height: {last_valid_block_height}")
    
    # Deserialize the transaction from base64
    try:
        swap_tx_bytes = base64.b64decode(swap_tx_base64)
        # Jupiter returns Versioned Transactions (v0) by default
        transaction = VersionedTransaction.from_bytes(swap_tx_bytes)
        print("✅ Transaction deserialized successfully")
        print("   Transaction type: Versioned Transaction (v0)")
        print(f"   Transaction size: {len(swap_tx_bytes)} bytes")
    except Exception as e:
        raise ValueError(f"Failed to deserialize transaction: {e}")

    # 4. Sign the transaction
    # -----------------------------------------------------------------
    # The transaction needs to be signed by the user's keypair
    print(f"\n{'='*70}")
    print("Step 4: Signing transaction")
    print(f"{'='*70}")
    
    try:
        # VersionedTransaction is signed during construction, not with .sign()
        # We need to create a new VersionedTransaction with the message and keypair
        signed_transaction = VersionedTransaction(transaction.message, [keypair])
        print(f"✅ Transaction signed by {owner}")
        transaction = signed_transaction
    except Exception as e:
        raise ValueError(f"Failed to sign transaction: {e}")
    
    # The transaction is now ready to be sent to the network
    # To send the transaction:
    #
    # tx_signature = client.send_transaction(transaction).value
    # print(f"✅ Transaction sent! Signature: {tx_signature}")
    #
    # To confirm the transaction:
    # confirmation = client.confirm_transaction(tx_signature)
    # print(f"Transaction confirmed: {confirmation}")
    
    print(f"\n{'='*70}")
    print("✅ Swap transaction ready to send!")
    print(f"{'='*70}")
    print("⚠️  Important: Review the swap details above before sending")
    print(f"   Expected price impact: {price_impact:.4f}%")
    print(f"   Slippage tolerance: {slippage_percent}%")
    print("\nTo send this transaction, use:")
    print("  tx_sig = client.send_transaction(transaction)")
    print(f"{'='*70}\n")

    return transaction