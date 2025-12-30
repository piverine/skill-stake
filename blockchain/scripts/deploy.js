const hre = require("hardhat");

async function main() {
    const SkillStake = await hre.ethers.getContractFactory("SkillStake");
    const [deployer, charity] = await hre.ethers.getSigners();
    // Use the second account as the charity address
    const skillStake = await SkillStake.deploy(charity.address);

    await skillStake.waitForDeployment();

    console.log(
        `SkillStake deployed to ${skillStake.target}`
    );
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
