/**
 * Interactive Solana wallet interface with token swap support.
 * Uses Jupiter aggregator and displays wallet balances.
 */

import { config } from 'dotenv';
import { Connection, Keypair, LAMPORTS_PER_SOL } from '@solana/web3.js';
import { existsSync, mkdirSync } from 'fs';
import { basename } from 'path';
import * as readline from 'readline';
import {
    loadKeypairFromJson,
    listPublicKeysWithPaths,
} from './wallet_utils.js';

// Load environment variables
config();

/** Get SOL balance for a wallet (returns null on error) */
async function getSolBalance(connection: Connection, keypair: Keypair): Promise<number | null> {
    try {
        const balance = await connection.getBalance(keypair.publicKey);
        return balance / LAMPORTS_PER_SOL;
    } catch (error) {
        console.log(`  Error fetching balance: ${error}`);
        return null;
    }
}

/** Display wallet address and balance */
async function displayWalletInfo(connection: Connection, keypair: Keypair): Promise<void> {
    console.log("\n" + "=".repeat(70));
    console.log("WALLET INFORMATION");
    console.log("=".repeat(70));
    console.log(`Address: ${keypair.publicKey.toBase58()}`);
    
    const balance = await getSolBalance(connection, keypair);
    if (balance !== null) {
        console.log(`Balance: ${balance.toFixed(4)} SOL`);
    } else {
        console.log("Balance: Unable to fetch");
    }
    
    console.log("=".repeat(70));
}

/** Create readline interface for user input */
function createReadlineInterface(): readline.Interface {
    return readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });
}

/** Get user input (keeps asking if required=true) */
async function getUserInput(rl: readline.Interface, prompt: string, required: boolean = true): Promise<string | null> {
    while (true) {
        const userInput = await new Promise<string>((resolve) => {
            rl.question(prompt, resolve);
        });
        
        const trimmedInput = userInput.trim();
        
        if (trimmedInput) {
            return trimmedInput;
        }
        
        if (!required) {
            return null;
        }
        
        console.log("  This field is required. Please enter a value.");
    }
}

/** Get user's swap action choice: "buy", "sell", or null to cancel */
async function getActionChoice(rl: readline.Interface): Promise<string | null> {
    console.log("\n" + "=".repeat(70));
    console.log("SWAP ACTION");
    console.log("=".repeat(70));
    console.log("1. Buy token with SOL");
    console.log("2. Sell token for SOL");
    console.log("0. Cancel");
    
    while (true) {
        const choice = await getUserInput(rl, "\nEnter your choice (0-2): ", true);
        
        if (choice === "0") {
            return null;
        } else if (choice === "1") {
            return "buy";
        } else if (choice === "2") {
            return "sell";
        } else {
            console.log("  Invalid choice. Please enter 0, 1, or 2.");
        }
    }
}

/** Get token mint address (supports shortcuts: USDC, USDT, RAY, ORCA) */
async function getTokenMintAddress(rl: readline.Interface): Promise<string | null> {
    console.log("\n" + "=".repeat(70));
    console.log("TOKEN SELECTION");
    console.log("=".repeat(70));
    console.log("Common tokens:");
    console.log("  USDC  - USD Coin");
    console.log("  USDT  - Tether USD");
    console.log("  RAY   - Raydium");
    console.log("  ORCA  - Orca");
    console.log("\nOr enter any Solana token mint address");
    console.log("(Enter 'cancel' to go back)");
    
    const COMMON_TOKENS: Record<string, string> = {
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE"
    };
    
    while (true) {
        const tokenInput = await getUserInput(rl, "\nToken (symbol or mint address): ", true);
        
        if (!tokenInput) {
            continue;
        }
        
        if (tokenInput.toLowerCase() === "cancel") {
            return null;
        }
        
        if (tokenInput.toUpperCase() in COMMON_TOKENS) {
            const mintAddress = COMMON_TOKENS[tokenInput.toUpperCase()];
            console.log(` Selected ${tokenInput.toUpperCase()}: ${mintAddress}`);
            return mintAddress;
        }
        
        if (tokenInput.length >= 32 && tokenInput.length <= 44) {
            console.log(" Token address format valid");
            return tokenInput;
        } else {
            console.log("  Invalid mint address format. Must be 32-44 characters.");
        }
    }
}

/** Let user select a wallet from available wallets */
async function selectWallet(rl: readline.Interface, walletsDir: string): Promise<Keypair | null> {
    const entries = listPublicKeysWithPaths(walletsDir);
    
    if (entries.length === 0) {
        console.log(`\n No wallets found in '${walletsDir}'`);
        console.log("\nTo create a wallet:");
        console.log(`  solana-keygen new --outfile ${walletsDir}\\wallet1.json`);
        return null;
    }
    
    console.log("\n" + "=".repeat(70));
    console.log("AVAILABLE WALLETS");
    console.log("=".repeat(70));
    
    const validWallets: string[] = [];
    entries.forEach(([pathStr, pubkeyStr], index) => {
        if (!pubkeyStr.startsWith("<error:")) {
            console.log(`${index + 1}. ${basename(pathStr)}`);
            console.log(`   ${pubkeyStr}`);
            validWallets.push(pathStr);
        } else {
            console.log(`${index + 1}. ${basename(pathStr)} - ERROR: ${pubkeyStr}`);
        }
    });
    
    if (validWallets.length === 0) {
        console.log("\n No valid wallets found");
        return null;
    }
    
    console.log("=".repeat(70));
    
    let walletPath: string;
    
    if (validWallets.length === 1) {
        walletPath = validWallets[0];
        console.log(`\n Using wallet: ${basename(walletPath)}`);
    } else {
        while (true) {
            const choice = await getUserInput(rl, `\nSelect wallet (1-${validWallets.length}): `, true);
            
            if (!choice) {
                continue;
            }
            
            try {
                const idx = parseInt(choice) - 1;
                
                if (idx >= 0 && idx < validWallets.length) {
                    walletPath = validWallets[idx];
                    break;
                } else {
                    console.log(`  Please enter a number between 1 and ${validWallets.length}`);
                }
            } catch (error) {
                console.log("  Please enter a valid number");
            }
        }
    }
    
    try {
        const keypair = loadKeypairFromJson(walletPath);
        console.log(" Wallet loaded successfully");
        return keypair;
    } catch (error) {
        console.log(` Failed to load wallet: ${error}`);
        return null;
    }
}

/** Main interactive swap interface */
async function main(): Promise<void> {
    const walletsDir = process.env.WALLETS_DIR || 'wallets';
    const rpcEndpoint = process.env.RPC_ENDPOINT || 'https://api.mainnet-beta.solana.com';
    
    if (!existsSync(walletsDir)) {
        mkdirSync(walletsDir, { recursive: true });
    }
    
    const rl = createReadlineInterface();
    
    try {
        const keypair = await selectWallet(rl, walletsDir);
        if (!keypair) return;
        
        const connection = new Connection(rpcEndpoint);
        await displayWalletInfo(connection, keypair);
    } finally {
        rl.close();
    }
}

process.on('SIGINT', () => {
    console.log("\n\n👋 Interrupted by user. Goodbye!");
    process.exit(0);
});

main()
    .then(() => setTimeout(() => process.exit(0), 100))
    .catch((error) => {
        if (error.message === 'SIGINT') {
            console.log("\n\n👋 Interrupted by user. Goodbye!");
        } else {
            console.error(`\n\n Fatal error: ${error}`);
        }
        setTimeout(() => process.exit(1), 100);
    });

export { main, displayWalletInfo, getSolBalance, selectWallet };

