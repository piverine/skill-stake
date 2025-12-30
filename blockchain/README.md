# SkillStake Smart Contract Deployment Guide

Since the automated environment had trouble with the Solidity compiler download, you can deploy the contracts manually from your local machine (assuming you have internet access to download the compiler).

## Prerequisites
- Node.js and npm/yarn installed.

## Steps

1.  **Navigate to the blockchain directory:**
    ```bash
    cd blockchain
    ```

2.  **Install Dependencies:**
    ```bash
    npm install
    ```
    *Note: If you run into peer dependency issues, try:* `npm install --legacy-peer-deps`

3.  **Compile the Contracts:**
    This step will download the Solidity compiler (solc 0.8.19) if it's missing.
    ```bash
    npx hardhat compile
    ```

4.  **Start a Local Blockchain Node:**
    Open a *new terminal window*, navigate to `blockchain`, and run:
    ```bash
    npx hardhat node
    ```
    *Keep this terminal running. It simulates the Ethereum network.*

5.  **Deploy the Contract:**
    In your original terminal (inside `blockchain`), run:
    ```bash
    npx hardhat run scripts/deploy.js --network localhost
    ```

6.  **Get the Contract Address:**
    The output should look like:
    ```
    SkillStake deployed to 0x5FbDB2315678afecb367f032d93F642f64180aa3
    ```
    (The address might be different).

7.  **Update Frontend Config:**
    Open `frontend/src/app/quiz/[id]/page.tsx` (or wherever the address is stored) and update the `CONTRACT_ADDRESS` constant:
    ```typescript
    const CONTRACT_ADDRESS = "0xYOUR_NEW_ADDRESS_HERE";
    ```

8.  **Restart Frontend:**
    If the frontend was already running, you might want to restart it to ensure everything is fresh.
    ```bash
    npm run dev
    ```

## Troubleshooting
- **"Nonce too high"**: If you restart the local node (`npx hardhat node`), you need to reset your Metamask account for "Localhost 8545" (Settings > Advanced > Clear Activity Tab Data) because the chain ID / nonces reset.
