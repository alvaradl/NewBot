/**
 * Wallet utilities for loading and managing Solana keypairs from JSON files.
 * Supports solana-keygen format (array of 64 bytes).
 */
import { Keypair } from '@solana/web3.js'
import { readFileSync, existsSync, readdirSync, statSync } from 'fs';
import { join, extname } from 'path';

/**
 * Load a Solana keypair from a JSON file (solana-keygen format).
 * @param jsonPath - Path to JSON file with keypair bytes
 * @returns Keypair object for transactions
 */

export function loadKeypairFromJson(jsonPath: string): Keypair {
    const raw = JSON.parse(readFileSync(jsonPath, 'utf-8'));
    
    if (!Array.isArray(raw)) {
        throw new Error(`Invalid key file format (expected array): ${jsonPath}`);
    }
    
    const secretKeyBytes = Uint8Array.from(raw);
    
    if (secretKeyBytes.length !== 64 && secretKeyBytes.length !== 32) {
        throw new Error(`Unexpected key length ${secretKeyBytes.length} in ${jsonPath}`);
    }
    
    return Keypair.fromSecretKey(secretKeyBytes);
}

/** Recursively find all JSON files in a directory */
function findJsonFiles(dir: string): string[] {
    const files: string[] = [];
    if (!existsSync(dir)) return files;

    for (const entry of readdirSync(dir)) {
        const fullPath = join(dir, entry);
        const stat = statSync(fullPath);
        
        if (stat.isDirectory()) {
            files.push(...findJsonFiles(fullPath));
        } else if (stat.isFile() && extname(entry) === '.json') {
            files.push(fullPath);
        }
    }
    
    return files.sort();
}

/**
 * Load all keypairs from a directory (recursively).
 * @param walletsDir - Directory path (default: "wallets")
 * @returns Array of successfully loaded keypairs
 */
export function loadAllWallets(walletsDir: string = 'wallets'): Keypair[] {
    if (!existsSync(walletsDir)) return [];

    const keypairs: Keypair[] = [];
    
    for (const jsonFile of findJsonFiles(walletsDir)) {
        try {
            keypairs.push(loadKeypairFromJson(jsonFile));
        } catch (error) {
            console.error(`Failed to load ${jsonFile}: ${error}`);
        }
    }

    return keypairs;
}

/**
 * Get wallet paths and public keys (or error messages).
 * @param walletsDir - Directory path (default: "wallets")
 * @returns Array of [filePath, publicKey | error] tuples
 */
export function listPublicKeysWithPaths(walletsDir: string = 'wallets'): Array<[string, string]> {
    if (!existsSync(walletsDir)) return [];

    const results: Array<[string, string]> = [];

    for (const jsonFile of findJsonFiles(walletsDir)) {
        try {
            const kp = loadKeypairFromJson(jsonFile);
            results.push([jsonFile, kp.publicKey.toBase58()]);
        } catch (error) {
            results.push([jsonFile, `<error: ${error}>`]);
        }
    }

    return results;
}

