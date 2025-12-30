const hre = require("hardhat");

async function main() {
    const CONTRACT_ADDRESS = "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82";

    try {
        const code = await hre.ethers.provider.getCode(CONTRACT_ADDRESS);
        if (code === "0x") {
            console.error("ERROR: No contract code found at " + CONTRACT_ADDRESS);
            console.error("The blockchain state was reset. You must re-deploy the contract.");
            process.exit(1);
        }

        // Get contract balance
        const balance = await hre.ethers.provider.getBalance(CONTRACT_ADDRESS);
        const blockNum = await hre.ethers.provider.getBlockNumber();
        console.log(`Current Block: ${blockNum}`);
        console.log(`Checking Address: ${CONTRACT_ADDRESS}`);
        console.log(`Contract Balance: ${hre.ethers.formatEther(balance)} ETH`);

        const SkillStake = await hre.ethers.getContractFactory("SkillStake");
        const contract = SkillStake.attach(CONTRACT_ADDRESS);

        // Check specific user state (from debug info)
        const userAddress = "0x9762e8a156e72b027d72f883270928c035544719"; // Approximation or passed arg
        // But since we don't know the exact full address, we rely on events.

        // List Stake Events
        const stakeEvents = await contract.queryFilter("Staked");
        console.log(`\nStaked Events: ${stakeEvents.length}`);
        stakeEvents.forEach(e => {
            console.log(` - User: ${e.args[0]}, Ans: ${hre.ethers.formatEther(e.args[2])} ETH, Block: ${e.blockNumber}`);
        });

        // List Withdrawn Events
        const withdrawEvents = await contract.queryFilter("Withdrawn");
        console.log(`\nWithdrawn Events: ${withdrawEvents.length}`);
        withdrawEvents.forEach(e => {
            console.log(` - User: ${e.args[0]}, Ans: ${hre.ethers.formatEther(e.args[2])} ETH, Block: ${e.blockNumber}`);
        });

    } catch (error) {
        console.error("Connection failed:", error.message);
    }
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
