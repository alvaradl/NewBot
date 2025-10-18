import { Transaction, VersionedTransaction, sendAndConfirmTransaction, PublicKey } from '@solana/web3.js'
import { NATIVE_MINT } from '@solana/spl-token'
import axios from 'axios'
import { connection, owner, fetchTokenAccountData, txVersion } from './config.js'
import { API_URLS } from '@raydium-io/raydium-sdk-v2'

interface SwapCompute {
    id: string
    success: true
    version: 'V0' | 'V1'
    openTime?: undefined
    msg: undefined
    data: {
      swapType: 'BaseIn' | 'BaseOut'
      inputMint: string
      inputAmount: string
      outputMint: string
      outputAmount: string
      otherAmountThreshold: string
      slippageBps: number
      priceImpactPct: number
      routePlan: {
        poolId: string
        inputMint: string
        outputMint: string
        feeMint: string
        feeRate: number
        feeAmount: string
      }[]
    }
  }

export async function get_token_quote(inputMint: string, outputMint: string, amount: number, slippage: number = 0.02): Promise<SwapCompute>{
    const txVersionStr = txVersion === 0 ? 'V0' : 'LEGACY'
    const { data: swapResponse } = await axios.get<SwapCompute>(
        `${
          API_URLS.SWAP_HOST
        }/compute/swap-base-in?inputMint=${inputMint}&outputMint=${outputMint}&amount=${amount}&slippageBps=${
          slippage * 100}&txVersion=${txVersionStr}`
      ) // Use the URL xxx/swap-base-in or xxx/swap-base-out to define the swap type. 
      console.log("Swap response: ", swapResponse)
      return swapResponse
}

export async function get_transaction(swapResponse: SwapCompute, isInputSol: boolean, isOutputSol: boolean, inputTokenAcc: PublicKey, outputTokenAcc: PublicKey): Promise<any>{
    const { data: priorityFee } = await axios.get<{
        id: string
        success: boolean
        data: { default: { vh: number; h: number; m: number } } 
      }>(`${API_URLS.BASE_HOST}${API_URLS.PRIORITY_FEE}`)
      console.log("Priority fee: ", priorityFee.data.default.h)

    const { data: swapTransactions } = await axios.post<{
        id: string
        version: string
        success: boolean
        data: { transaction: string }[]
      }>(`${API_URLS.SWAP_HOST}/transaction/swap-base-in`, {
        computeUnitPriceMicroLamports: String(priorityFee.data.default.h),
        swapResponse,
        txVersion,
        wallet: owner.publicKey.toBase58(),
        wrapSol: isInputSol,
        unwrapSol: isOutputSol, // true means output mint receive sol, false means output mint received wsol
        inputAccount: isInputSol ? undefined : inputTokenAcc?.toBase58(),
        outputAccount: isOutputSol ? undefined : outputTokenAcc?.toBase58(),
      })
    console.log("Swap transactions: ", swapTransactions)
    return swapTransactions
}
async function main(){
    const inputMint = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' // USDC
    const outputMint = 'So11111111111111111111111111111111111111112'  // SOL
    
    // Get all token accounts for the wallet
    const tokenAccountData = await fetchTokenAccountData()
    
    // Find the USDC token account
    const inputTokenAccount = tokenAccountData.tokenAccounts.find(
        acc => acc.mint.toBase58() === inputMint
    )
    
    if (!inputTokenAccount || !inputTokenAccount.publicKey) {
        console.log('⚠️  USDC token account not found. You may need to create it or you don\'t have USDC.')
        return
    }
    
    console.log('Input token account (USDC):', inputTokenAccount.publicKey.toBase58())
    console.log('USDC balance:', inputTokenAccount.amount.toString())
    
    // Get swap quote
    const swapResponse = await get_token_quote(
        inputMint,
        outputMint,
        100000000  // 100 USDC (100 * 10^6)
    )
    
    // Get swap transaction
    const swapTransactions = await get_transaction(
        swapResponse, 
        false,                        // isInputSol = false (we're swapping USDC)
        true,                         // isOutputSol = true (we want SOL, not wrapped SOL)
        inputTokenAccount.publicKey,  // Our USDC token account
        undefined                     // undefined because output is SOL
    )
    
    console.log('Swap transaction ready!')
}

main().catch(console.error)