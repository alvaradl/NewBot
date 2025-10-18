/**
 * pre_bonded_trading.ts
 * Purpose: Pump.fun-first pre-bonded token buyer (extensible adapter architecture).
 *
 * USAGE WARNING: Test thoroughly on devnet or with small amounts. Pre-bonded tokens
 * are minted by platform-specific programs; incorrect instruction layouts or missing
 * accounts can result in lost funds.
 *
 * HOW THIS FILE IS STRUCTURED:
 * - exports: getPreBondedTokenInfo, buildBuyTx, executeBuyTx, watchAndBuy, registerPlatform
 * - Platform adapters (pumpfun, extendable)
 * - config: env-driven
 *
 * Safety: simulate transactions before sending; use dryRun=true during development.
 */

import {
  Connection,
  PublicKey,
  Transaction,
  TransactionInstruction,
  SystemProgram,
  Keypair,
  LAMPORTS_PER_SOL,
  SendOptions,
  ConfirmOptions,
  ParsedTransactionWithMeta,
} from '@solana/web3.js'
import {
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
  getAssociatedTokenAddress,
  createAssociatedTokenAccountInstruction,
  NATIVE_MINT,
  createSyncNativeInstruction,
  createCloseAccountInstruction,
} from '@solana/spl-token'
import BN from 'bn.js'

// ============================================================================
// Types & Interfaces
// ============================================================================

export type PlatformType = 'pumpfun' | 'axiom' | 'unknown'
export type TokenStatus = 'prebonded' | 'graduated' | 'unknown'

export interface PreBondedInfo {
  platform: PlatformType
  bondingProgram: PublicKey
  bondingPda: PublicKey
  mint: PublicKey
  decimals: number
  priceLamports: BN | number | null
  reserveLamports: BN | null
  capLamports: BN | null
  status: TokenStatus
  raw: any
}

export interface SignerLike {
  publicKey: PublicKey
  signTransaction?: (tx: Transaction) => Promise<Transaction>
  signAllTransactions?: (txs: Transaction[]) => Promise<Transaction[]>
}

export interface PlatformAdapter {
  name: string
  programIds: PublicKey[]
  detect: (connection: Connection, mint: PublicKey) => Promise<PreBondedInfo | null>
  buildBuyInstruction: (
    info: PreBondedInfo,
    buyer: PublicKey,
    buyerAta: PublicKey,
    lamports: BN | number
  ) => Promise<TransactionInstruction>
}

export interface WatchAndBuyParams {
  connection: Connection
  payer: SignerLike | Keypair
  mint: PublicKey
  targetLamports: BN | number
  maxSlippagePct?: number
  timeoutMs?: number
  privateRpc?: string
  onTx?: (signature: string) => void
  platformOverride?: PlatformType
  dryRun?: boolean
}

// ============================================================================
// Configuration
// ============================================================================

// Known Pump.fun program IDs (can be updated as needed)
export const DEFAULT_PUMPFUN_PROGRAMS = [
  new PublicKey('6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'), // Main Pump.fun program
]

// Optional: Pump.fun API endpoint for metadata
export const DATA_API_URL = process.env.PUMPFUN_API_URL || 'https://pumpportal.fun/api'

// Confirmation options
export const DEFAULT_CONFIRM_OPTIONS: ConfirmOptions = {
  commitment: 'confirmed',
  preflightCommitment: 'confirmed',
}

// ============================================================================
// Platform Registry
// ============================================================================

const platformAdapters: Map<PlatformType, PlatformAdapter> = new Map()

export function registerPlatform(adapter: PlatformAdapter): void {
  platformAdapters.set(adapter.name as PlatformType, adapter)
}

// ============================================================================
// Pump.fun Platform Adapter
// ============================================================================

const PUMPFUN_GLOBAL = new PublicKey('4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf')
const PUMPFUN_FEE_RECIPIENT = new PublicKey('CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM')
const PUMPFUN_EVENT_AUTHORITY = new PublicKey('Ce6TQqeHC9p8KetsN6JsjHK7UTZk7nasjjnr7XxXp9F1')
const SYSTEM_TOKEN_PROGRAM = new PublicKey('11111111111111111111111111111111')

class PumpfunAdapter implements PlatformAdapter {
  name: PlatformType = 'pumpfun'
  programIds = DEFAULT_PUMPFUN_PROGRAMS

  async detect(connection: Connection, mint: PublicKey): Promise<PreBondedInfo | null> {
    try {
      // Derive bonding curve PDA
      const bondingPda = await this.deriveBondingCurvePda(mint)
      
      // Try to fetch bonding curve account
      const accountInfo = await connection.getAccountInfo(bondingPda)
      if (!accountInfo) {
        return null
      }

      // Check if account is owned by Pump.fun program
      const isPumpfun = this.programIds.some(progId => accountInfo.owner.equals(progId))
      if (!isPumpfun) {
        return null
      }

      // Parse bonding curve data (simplified - actual layout may vary)
      // TODO: Verify exact layout from Pump.fun program
      const data = accountInfo.data
      
      // Get mint info for decimals
      const mintInfo = await connection.getParsedAccountInfo(mint)
      const decimals = (mintInfo.value?.data as any)?.parsed?.info?.decimals || 9

      // Try to fetch price from API or parse from account data
      let priceLamports: BN | null = null
      let reserveLamports: BN | null = null
      
      try {
        // Attempt to get data from Pump.fun API
        const apiData = await this.fetchPumpfunApiData(mint)
        if (apiData) {
          priceLamports = new BN(apiData.virtual_sol_reserves || 0)
          reserveLamports = new BN(apiData.virtual_sol_reserves || 0)
        }
      } catch (e) {
        // Fall back to parsing on-chain data if API fails
        console.warn('Failed to fetch Pump.fun API data, using on-chain data')
      }

      // Check if graduated (migrated to Raydium)
      const status: TokenStatus = accountInfo.lamports > 0 ? 'prebonded' : 'graduated'

      return {
        platform: 'pumpfun',
        bondingProgram: this.programIds[0],
        bondingPda,
        mint,
        decimals,
        priceLamports,
        reserveLamports,
        capLamports: new BN(85 * LAMPORTS_PER_SOL), // Pump.fun typically graduates at ~85 SOL
        status,
        raw: {
          accountData: data,
          owner: accountInfo.owner.toBase58(),
        },
      }
    } catch (error) {
      console.error('Error detecting Pump.fun token:', error)
      return null
    }
  }

  async buildBuyInstruction(
    info: PreBondedInfo,
    buyer: PublicKey,
    buyerAta: PublicKey,
    lamports: BN | number
  ): Promise<TransactionInstruction> {
    // TODO: Verify exact instruction layout from verified Pump.fun transactions
    // This is a template based on common Pump.fun buy patterns
    
    const lamportsBN = typeof lamports === 'number' ? new BN(lamports) : lamports
    
    // Derive associated bonding curve PDA
    const associatedBondingCurve = await getAssociatedTokenAddress(
      info.mint,
      info.bondingPda,
      true // allowOwnerOffCurve
    )

    // Build instruction discriminator for "buy" (typically first 8 bytes)
    // TODO: Confirm exact discriminator from Pump.fun program IDL or verified tx
    const discriminator = Buffer.from([0x66, 0x06, 0x3d, 0x12, 0x01, 0xda, 0xeb, 0xea]) // Placeholder
    
    // Build instruction data
    const instructionData = Buffer.concat([
      discriminator,
      lamportsBN.toArrayLike(Buffer, 'le', 8), // Amount in lamports
      new BN(1000000).toArrayLike(Buffer, 'le', 8), // Max token amount (with slippage)
    ])

    // Build account keys
    const keys = [
      { pubkey: PUMPFUN_GLOBAL, isSigner: false, isWritable: false },
      { pubkey: PUMPFUN_FEE_RECIPIENT, isSigner: false, isWritable: true },
      { pubkey: info.mint, isSigner: false, isWritable: false },
      { pubkey: info.bondingPda, isSigner: false, isWritable: true },
      { pubkey: associatedBondingCurve, isSigner: false, isWritable: true },
      { pubkey: buyerAta, isSigner: false, isWritable: true },
      { pubkey: buyer, isSigner: true, isWritable: true },
      { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
      { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false },
      { pubkey: SystemProgram.programId, isSigner: false, isWritable: false },
      { pubkey: PUMPFUN_EVENT_AUTHORITY, isSigner: false, isWritable: false },
      { pubkey: info.bondingProgram, isSigner: false, isWritable: false },
    ]

    return new TransactionInstruction({
      programId: info.bondingProgram,
      keys,
      data: instructionData,
    })
  }

  private async deriveBondingCurvePda(mint: PublicKey): Promise<PublicKey> {
    // Derive bonding curve PDA using standard seeds
    const [pda] = await PublicKey.findProgramAddress(
      [Buffer.from('bonding-curve'), mint.toBuffer()],
      this.programIds[0]
    )
    return pda
  }

  private async fetchPumpfunApiData(mint: PublicKey): Promise<any> {
    try {
      const response = await fetch(`${DATA_API_URL}/data/coin/${mint.toBase58()}`)
      if (!response.ok) return null
      return await response.json()
    } catch {
      return null
    }
  }
}

// Register Pump.fun adapter by default
registerPlatform(new PumpfunAdapter())

// ============================================================================
// Core Functions
// ============================================================================

/**
 * Detects if a mint is pre-bonded to a known platform (Pump.fun, etc.)
 * @returns PreBondedInfo if detected, null otherwise
 */
export async function getPreBondedTokenInfo(
  connection: Connection,
  mint: PublicKey
): Promise<PreBondedInfo | null> {
  // Validate mint
  if (!PublicKey.isOnCurve(mint.toBuffer())) {
    throw new Error('Invalid mint public key')
  }

  // Try each registered platform adapter
  for (const [_name, adapter] of platformAdapters) {
    try {
      const info = await adapter.detect(connection, mint)
      if (info) {
        return info
      }
    } catch (error) {
      console.warn(`Platform ${adapter.name} detection failed:`, error)
    }
  }

  return null
}

/**
 * Builds a buy transaction for a pre-bonded token
 * @param dryRun If true, only simulates without building full transaction
 */
export async function buildBuyTx(
  connection: Connection,
  payer: SignerLike | Keypair,
  info: PreBondedInfo,
  solToSpendLamports: BN | number,
  options?: { dryRun?: boolean }
): Promise<Transaction> {
  const payerPubkey = payer.publicKey

  // Get adapter for this platform
  const adapter = platformAdapters.get(info.platform)
  if (!adapter) {
    throw new Error(`No adapter registered for platform: ${info.platform}`)
  }

  // Get or create ATA for the token
  const buyerAta = await getAssociatedTokenAddress(
    info.mint,
    payerPubkey,
    false,
    TOKEN_PROGRAM_ID,
    ASSOCIATED_TOKEN_PROGRAM_ID
  )

  const tx = new Transaction()

  // Check if ATA exists
  const ataInfo = await connection.getAccountInfo(buyerAta)
  if (!ataInfo) {
    // Create ATA
    const createAtaIx = createAssociatedTokenAccountInstruction(
      payerPubkey,
      buyerAta,
      payerPubkey,
      info.mint,
      TOKEN_PROGRAM_ID,
      ASSOCIATED_TOKEN_PROGRAM_ID
    )
    tx.add(createAtaIx)
  }

  // Build platform-specific buy instruction
  const buyIx = await adapter.buildBuyInstruction(
    info,
    payerPubkey,
    buyerAta,
    solToSpendLamports
  )
  tx.add(buyIx)

  // Set fee payer and get recent blockhash
  tx.feePayer = payerPubkey
  const { blockhash } = await connection.getLatestBlockhash()
  tx.recentBlockhash = blockhash

  // Simulate if requested
  if (options?.dryRun) {
    try {
      const simulation = await connection.simulateTransaction(tx)
      console.log('Simulation result:', simulation)
      if (simulation.value.err) {
        throw new Error(`Simulation failed: ${JSON.stringify(simulation.value.err)}`)
      }
    } catch (error) {
      console.error('Transaction simulation failed:', error)
      throw error
    }
  }

  return tx
}

/**
 * Signs and executes a buy transaction
 */
export async function executeBuyTx(
  connection: Connection,
  payer: SignerLike | Keypair,
  tx: Transaction,
  signers?: Keypair[],
  options?: ConfirmOptions
): Promise<string> {
  const confirmOptions = { ...DEFAULT_CONFIRM_OPTIONS, ...options }

  // Sign transaction
  if ('signTransaction' in payer && typeof payer.signTransaction === 'function') {
    // Wallet adapter signing
    tx = await payer.signTransaction(tx)
  } else if (payer instanceof Keypair) {
    // Keypair signing
    const allSigners = [payer, ...(signers || [])]
    tx.sign(...allSigners)
  } else {
    throw new Error('Payer must be Keypair or have signTransaction method')
  }

  // Send and confirm
  const signature = await connection.sendRawTransaction(tx.serialize(), {
    skipPreflight: false,
    preflightCommitment: confirmOptions.preflightCommitment,
  })

  await connection.confirmTransaction(signature, confirmOptions.commitment)

  return signature
}

/**
 * High-level helper: watch token status and execute buy when conditions are met
 */
export async function watchAndBuy(params: WatchAndBuyParams): Promise<string | null> {
  const {
    connection,
    payer,
    mint,
    targetLamports,
    maxSlippagePct = 5,
    timeoutMs = 60000,
    dryRun = false,
    onTx,
  } = params

  const startTime = Date.now()

  while (Date.now() - startTime < timeoutMs) {
    try {
      // Get token info
      const info = await getPreBondedTokenInfo(connection, mint)
      
      if (!info) {
        console.log('Token not found or not pre-bonded, waiting...')
        await new Promise(resolve => setTimeout(resolve, 2000))
        continue
      }

      if (info.status === 'graduated') {
        console.log('Token has graduated to Raydium')
        // TODO: Could switch to Raydium flow here
        return null
      }

      // Build and execute transaction
      console.log(`Buying ${targetLamports} lamports worth of ${mint.toBase58()}`)
      
      const tx = await buildBuyTx(connection, payer, info, targetLamports, { dryRun })
      
      if (dryRun) {
        console.log('Dry run complete, not executing')
        return null
      }

      const signature = await executeBuyTx(connection, payer, tx)
      console.log('Buy transaction successful:', signature)
      
      if (onTx) {
        onTx(signature)
      }

      return signature
    } catch (error) {
      console.error('Error in watchAndBuy:', error)
      await new Promise(resolve => setTimeout(resolve, 2000))
    }
  }

  throw new Error('Timeout waiting for buy conditions')
}

// ============================================================================
// Demo / Testing
// ============================================================================

/**
 * Demo function showing usage (commented out for production)
 * Uncomment and run with: ts-node pre_bonded_trading.ts --demo
 */
/*
async function demo() {
  const connection = new Connection('https://api.mainnet-beta.solana.com', 'confirmed')
  
  // Load keypair (NEVER commit real keys!)
  const keypairPath = process.env.KEYPAIR_PATH || './test-keypair.json'
  const secretKey = JSON.parse(require('fs').readFileSync(keypairPath, 'utf-8'))
  const payer = Keypair.fromSecretKey(new Uint8Array(secretKey))

  console.log('Payer:', payer.publicKey.toBase58())

  // Example mint (replace with actual token)
  const mint = new PublicKey('YourPumpFunTokenMintHere')

  // 1. Get token info
  console.log('\n--- Getting token info ---')
  const info = await getPreBondedTokenInfo(connection, mint)
  if (!info) {
    console.log('Token not found or not pre-bonded')
    return
  }
  console.log('Token info:', info)

  // 2. Dry run a buy
  console.log('\n--- Dry run buy (0.01 SOL) ---')
  const buyAmount = 0.01 * LAMPORTS_PER_SOL
  const tx = await buildBuyTx(connection, payer, info, buyAmount, { dryRun: true })
  console.log('Transaction built and simulated successfully')

  // 3. Execute if --confirm flag passed
  if (process.argv.includes('--confirm')) {
    console.log('\n--- Executing real buy ---')
    const signature = await executeBuyTx(connection, payer, tx)
    console.log('Success! Signature:', signature)
  } else {
    console.log('\nPass --confirm to execute the real transaction')
  }
}

if (require.main === module && process.argv.includes('--demo')) {
  demo().catch(console.error)
}
*/


