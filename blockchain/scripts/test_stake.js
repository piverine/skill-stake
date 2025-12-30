const hre = require("hardhat");

async function main() {
    const CONTRACT_ADDRESS = "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82";
    const [deployer] = await hre.ethers.getSigners();

    console.log("Testing stake with account:", deployer.address);

    const SkillStake = await hre.ethers.getContractFactory("SkillStake");
    const contract = SkillStake.attach(CONTRACT_ADDRESS);

    const quizId = hre.ethers.keccak256(hre.ethers.toUtf8Bytes("test-quiz-id"));
    const stakeAmount = hre.ethers.parseEther("0.001");

    try {
        console.log(`Staking ${hre.ethers.formatEther(stakeAmount)} ETH...`);
        const tx = await contract.stake(quizId, { value: stakeAmount });
        console.log("Tx sent:", tx.hash);
        await tx.wait();
        console.log("Stake SUCCESS!");
    } catch (error) {
        console.error("Stake FAILED:", error.message);
        if (error.data) {
            console.error("Revert data:", error.data);
        }
    }
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
