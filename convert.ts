import bs58 from 'bs58';
import { readFileSync } from 'fs';

/**
 * Reads a Solana wallet secret key from a json file,
 * parses it as a Uint8Array, and encodes it to a base58 string.
 * Returns the base58-encoded secret key, suitable for use with Keypair.fromSecretKey(bs58.decode(...))
 */
export function convertSecretKeyToBase58(): string {
    // Read the secret key file as a utf-8 string
    const secret = readFileSync('wallets/wallet1.json', 'utf-8');
    // Parse the JSON array and convert it to Uint8Array
    const secretKey = Uint8Array.from(JSON.parse(secret));
    // Encode the Uint8Array secret key to a base58 string
    return bs58.encode(secretKey);
}
