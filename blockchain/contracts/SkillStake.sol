// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title SkillStake
 * @dev Manages staking, attempting, and payouts for the Skill Stake platform.
 */
contract SkillStake {
    address public owner;
    address public charityAddress;
    uint256 public constant STAKE_AMOUNT = 0.01 ether;

    // Mapping from Quiz ID to User address to Stake status
    // true = staked, false = not staked or withdrawn
    mapping(bytes32 => mapping(address => bool)) public hasStaked;

    event Staked(address indexed user, bytes32 indexed quizId, uint256 amount);
    event Withdrawn(address indexed user, bytes32 indexed quizId, uint256 amount);
    event Donated(address indexed user, bytes32 indexed quizId, uint256 amount);

    constructor(address _charityAddress) {
        owner = msg.sender;
        charityAddress = _charityAddress;
    }

    /**
     * @dev User stakes ETH to attempt a quiz.
     * @param quizId The unique identifier of the quiz (hash of PDF + User?).
     */
    function stake(bytes32 quizId) external payable {
        require(msg.value == STAKE_AMOUNT, "Must stake exactly 0.01 ETH");
        require(!hasStaked[quizId][msg.sender], "Already staked for this quiz");

        hasStaked[quizId][msg.sender] = true;
        emit Staked(msg.sender, quizId, msg.value);
    }

    /**
     * @dev User withdraws their stake after passing the quiz.
     * Requires a valid signature from the backend oracle.
     * @param quizId The quiz ID.
     * @param signature Cryptographic signature from admin proving pass.
     */
    function withdraw(bytes32 quizId, bytes calldata signature) external {
        require(hasStaked[quizId][msg.sender], "No active stake found");
        
        // Verify signature
        bytes32 messageHash = keccak256(abi.encodePacked(msg.sender, quizId, "PASSED"));
        bytes32 ethSignedMessageHash = getEthSignedMessageHash(messageHash);
        require(recoverSigner(ethSignedMessageHash, signature) == owner, "Invalid signature");

        // Update state before transfer to prevent reentrancy
        hasStaked[quizId][msg.sender] = false;

        // refund stake
        payable(msg.sender).transfer(STAKE_AMOUNT);
        emit Withdrawn(msg.sender, quizId, STAKE_AMOUNT);
    }

    /**
     * @dev Forfeits the stake to charity.
     * Can be called by the user (giving up) or potentially the admin (after timeout/failures).
     * For MVP, we'll let the user call it or Admin call it with proof?
     * Let's simplfy: Only admin can force donation? Or user initiates?
     * For now: Admin can force donation if 3 attempts failed (simulated). 
     * Or simpler: User calls this to "give up" and clear state?
     * Let's make it callable by admin to enforce rules.
     */
    function forfeit(bytes32 quizId, address user) external {
        require(msg.sender == owner, "Only admin can enforce forfeiture");
        require(hasStaked[quizId][user], "No active stake found");

        hasStaked[quizId][user] = false;
        
        payable(charityAddress).transfer(STAKE_AMOUNT);
        emit Donated(user, quizId, STAKE_AMOUNT);
    }

    // --- Signature Verification Helpers ---

    function getEthSignedMessageHash(bytes32 _messageHash) public pure returns (bytes32) {
        return keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", _messageHash));
    }

    function recoverSigner(bytes32 _ethSignedMessageHash, bytes memory _signature) public pure returns (address) {
        (bytes32 r, bytes32 s, uint8 v) = splitSignature(_signature);
        return ecrecover(_ethSignedMessageHash, v, r, s);
    }

    function splitSignature(bytes memory sig) public pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(sig.length == 65, "invalid signature length");
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
    }
    
    // Allow contract to receive ETH
    receive() external payable {}
}
