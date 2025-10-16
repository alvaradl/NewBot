import bs58 from 'bs58';
import { readFileSync } from 'fs';
export function convertSecretKeyToBase58(): string {
    const secret = readFileSync('wallets/wallet1.json', 'utf-8');
    const secretKey = Uint8Array.from(JSON.parse(secret));

    return bs58.encode(secretKey);
}
