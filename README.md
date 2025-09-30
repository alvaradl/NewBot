### MemeSniper - Automated Memecoin Trading Bot

MemeSniper — a compact, user-configurable bot preset designed to help savvy traders automatically attempt fast buys of newly-listed meme tokens on decentralized exchanges. Set your budget, slippage tolerance, gas strategies, and pre- and post-trade safety checks; the bot will monitor pools and memecoin launches, execute buys that match your rules, and log outcomes for review. Built with careful attention to transaction safety and transparency — not a get-rich-quick guarantee, but a tool to apply a consistent, repeatable strategy while you watch the market.

This is a lightweight, beginner‑friendly Python starter to manage multiple Solana wallets and prepare for building a trading bot. It focuses on local development, clarity, and safe handling of secrets.

### Features
- Load multiple wallets from `wallets/` folder (`*.json` keypairs)
- Print public keys to verify successful loading
- Uses `solana`/`solders`, `python-dotenv`, `aiohttp`, and `requests`

### Prerequisites
- Windows Subsystem for Linux (WSL)
- Python 3.10+
- Solana CLI, Rust, Node.js, and Anchor CLI

### 1) Install WSL and Development Dependencies (Windows)
[Installation Documentation](https://solana.com/docs/intro/installation#installation)
1. Install WSL by running this command in Windows PowerShell:
```powershell
wsl --install
```
After installation completes, the Ubuntu(Linux) terminal will be installed and used to follow the WSL setup prompts.

2. Open the new Ubuntu  and install the Solana CLI and other dependencies:
```bash
curl --proto '=https' --tlsv1.2 -sSfL https://solana-install.solana.workers.dev | bash
```

3. Verify the installations by checking versions:
```bash
rustc --version && solana --version && anchor --version && node --version && yarn --version
```

You should see output similar to:
```
rustc 1.86.0 (05f9846f8 2025-03-31)
solana-cli 2.2.12 (src:0315eb6a; feat:1522022101, client:Agave)
anchor-cli 0.31.1
v23.11.0
1.22.1
```

4. Install Python dependencies
```bash
python -m venv .venv
.venv\\Scripts\\activate  # Windows PowerShell
pip install -r requirements.txt
```

### 2) Generate and Configure Wallets

#### Step 1 — Create Wallet Directory
First, create a dedicated folder to store all your wallet keypairs. In WSL:

```bash
mkdir -p /mnt/c/GitHub/NewBot/wallets
```

#### Step 2 — Create Main Wallet
Generate your main wallet that will hold your primary funds:

```bash
solana-keygen new --outfile /mnt/c/GitHub/NewBot/wallets/main.json
```

During wallet creation:
- You'll be prompted to enter a BIP39 passphrase (optional but adds extra security)
- IMPORTANT: Save the 12-word seed phrase in a secure location
- Note the public key shown - this is your wallet address

#### Step 3 — Set Default Signer
Configure this as your default signing wallet:

```bash
solana config set --keypair /mnt/c/GitHub/NewBot/wallets/main.json
```

You can now quickly check your main wallet's address anytime:
```bash
solana address
```

#### Step 4 — Create Additional Trading Wallets (Optional)
For trading strategies requiring multiple wallets:

```bash
solana-keygen new --outfile /mnt/c/GitHub/NewBot/wallets/trader1.json --no-bip39-passphrase
solana-keygen new --outfile /mnt/c/GitHub/NewBot/wallets/trader2.json --no-bip39-passphrase
```

You can verify any wallet's public key using:
```bash
solana-keygen pubkey /mnt/c/GitHub/NewBot/wallets/trader1.json
```

Notes:
- The `--no-bip39-passphrase` flag is used for automated trading wallets to avoid manual passphrase entry
- Main wallet should use a passphrase for better security
- Keep your seed phrases and JSON files secure and never share them

Notes:
- The files above are JSON-encoded byte arrays of the secret key. Keep them private.
- For existing keypairs created by Solana CLI, you can copy their `.json` files into `wallets/`.

### 3) Loading wallets in Python
This starter uses `Keypair.from_bytes` with JSON files that contain the raw 64-byte secret key array produced by Solana CLI. See `wallet_utils.py` for the helper and `main.py` for usage.

### 4) Run the bot starter
```bash
python main.py
```
You should see the discovered wallet public keys printed.

### Environment variables (optional)
Create a `.env` file for API keys and configuration. Example:
```
RPC_ENDPOINT=https://api.mainnet-beta.solana.com
```
The `.env` file is ignored by git.

### Project structure
```
NewBot/
  main.py
  wallet_utils.py
  requirements.txt
  .gitignore
  .env        # not committed
  wallets/    # *.json keypairs, not committed
```

### Security reminders
- Never commit `.env` or `wallets/*.json`.
- Treat private keys as highly sensitive.

---

Original note: This project was bootstrapped from a preset to experiment with automated trading ideas. This README now documents a minimal Solana multi-wallet Python setup.
