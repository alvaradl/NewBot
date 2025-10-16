const bs58Module = require('bs58');
const bs58 = bs58Module.default || bs58Module;
const secret = require('fs').readFileSync(`wallets/wallet1.json`, 'utf-8');
const secretKey = Uint8Array.from(JSON.parse(secret));
console.log(bs58.encode(secretKey));