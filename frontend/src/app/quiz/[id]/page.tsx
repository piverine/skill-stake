'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAccount, useWriteContract, useReadContract, useWaitForTransactionReceipt, useBalance } from 'wagmi';
import { parseEther, keccak256, toHex } from 'viem';
import { WalletConnect } from '@/components/WalletConnect';
import axios from 'axios';
import { useAuth } from '@clerk/nextjs';

// ABI for SkillStake.sol (Minimal)
const CONTRACT_ABI = [
    {
        "inputs": [{ "internalType": "bytes32", "name": "quizId", "type": "bytes32" }],
        "name": "stake",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{ "internalType": "bytes32", "name": "", "type": "bytes32" }, { "internalType": "address", "name": "", "type": "address" }],
        "name": "hasStaked",
        "outputs": [{ "internalType": "bool", "name": "", "type": "bool" }],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            { "internalType": "bytes32", "name": "quizId", "type": "bytes32" },
            { "internalType": "bytes", "name": "signature", "type": "bytes" }
        ],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
];

// Replace with deployed address (Dummy for now)
const CONTRACT_ADDRESS = "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82";

export default function QuizPage() {
    const params = useParams();
    const quizId = params.id as string;
    const { address, isConnected, chainId } = useAccount(); // Add chainId here
    const { getToken, isLoaded, isSignedIn } = useAuth();

    // Debugging: Contract Balance
    const { data: contractBalance } = useBalance({
        address: CONTRACT_ADDRESS,
    });

    const [quiz, setQuiz] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [answers, setAnswers] = useState<Record<string, number>>({});
    const [score, setScore] = useState<number | null>(null);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    const [localStakeSuccess, setLocalStakeSuccess] = useState(false);

    // Wagmi Hooks
    const [txHash, setTxHash] = useState<`0x${string}` | undefined>(undefined);
    const [txType, setTxType] = useState<'STAKE' | 'CLAIM' | null>(null);
    const { writeContractAsync, isPending } = useWriteContract();
    const { isLoading: isConfirming, isSuccess: isConfirmed, data: receipt } = useWaitForTransactionReceipt({ hash: txHash });

    // Convert quiz UUID string to bytes32 for contract using keccak256 hash
    const quizIdBytes32 = keccak256(toHex(quizId));

    // Check if user has staked
    const { data: hasStakedOnChain, refetch: refetchStakeStatus } = useReadContract({
        address: CONTRACT_ADDRESS,
        abi: CONTRACT_ABI,
        functionName: 'hasStaked',
        args: [quizIdBytes32, address as `0x${string}`],
    });

    useEffect(() => {
        if (isConfirmed && receipt) {
            if (receipt.status === 'reverted') {
                alert("Transaction Failed! The contract reverted the transaction.");
                setTxType(null);
                setTxHash(undefined);
                return;
            }

            // Refetch stake status to update UI immediately
            refetchStakeStatus();

            if (txType === 'CLAIM') {
                alert("Success! Stake claimed successfully (0.001 ETH refunded).");
                window.location.href = '/dashboard';
            } else if (txType === 'STAKE') {
                console.log("Staking confirmed, starting quiz...");
                refetchStakeStatus(); // Ensure we refetch again
                setLocalStakeSuccess(true);
            }
            // Reset types
            setTxType(null);
            setTxHash(undefined);
        }
    }, [isConfirmed, receipt, txHash, refetchStakeStatus, txType]);

    useEffect(() => {
        if (!isLoaded) return;

        const fetchQuiz = async () => {
            try {
                if (!isSignedIn) {
                    setLoading(false);
                    return;
                }
                const token = await getToken();
                const res = await axios.get(`http://localhost:8000/api/v1/quiz/${quizId}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setQuiz(res.data);
            } catch (err) {
                console.error("Failed to load quiz", err);
            } finally {
                setLoading(false);
            }
        };

        if (quizId) {
            fetchQuiz();
        } else {
            setLoading(false);
        }
    }, [quizId, isLoaded, isSignedIn]); // Stable dependencies

    // ... existing ...

    // ... existing ...

    const handleClaim = async () => {
        if (!quiz?.signature) {
            alert("No signature found. Cannot claim.");
            return;
        }

        // Ensure signature has 0x prefix
        const signature = quiz.signature.startsWith('0x') ? quiz.signature : `0x${quiz.signature}`;

        try {
            setTxType('CLAIM');
            const hash = await writeContractAsync({
                address: CONTRACT_ADDRESS,
                abi: CONTRACT_ABI,
                functionName: 'withdraw',
                args: [quizIdBytes32, signature as `0x${string}`],
            });
            console.log("Claim tx sent:", hash);
            setTxHash(hash);
        } catch (error: any) {
            console.error("Claim failed:", error);
            setTxType(null);
            const msg = error?.message || "Transaction rejected or failed";
            alert(`Failed to claim stake: ${msg}`);
        }
    };

    const handleStake = async () => {
        try {
            console.log("Initiating stake for quiz:", quizId);
            setTxType('STAKE');
            const hash = await writeContractAsync({
                address: CONTRACT_ADDRESS,
                abi: CONTRACT_ABI,
                functionName: 'stake',
                args: [quizIdBytes32],
                value: parseEther('0.001'),
            });
            console.log("Staking tx sent:", hash);
            setTxHash(hash);
        } catch (error: any) {
            console.error("Staking failed:", error);
            setTxType(null);
            alert(`Failed to initiate staking: ${error?.message || "Unknown error"}`);
        }
    };

    const handleSubmit = async () => {
        try {
            const token = await getToken(); // Get fresh token

            if (!quiz || !quiz.questions) return;

            // Map answers to ordered list matching quiz.questions
            const formattedAnswers = quiz.questions.map((q: any) =>
                answers[q.question_id] !== undefined ? answers[q.question_id] : -1
            );

            // Check if all answered
            if (formattedAnswers.some((a: number) => a === -1)) {
                alert("Please answer all questions before submitting.");
                return;
            }

            // Include wallet address for signature generation
            const res = await axios.post(`http://localhost:8000/api/v1/quiz/${quizId}/submit`, {
                quiz_id: quizId,
                user_answers: formattedAnswers,
                wallet_address: address
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            console.log("Submission response:", res.data);
            setScore(res.data.score);
            // Update quiz with signature if passed
            setQuiz(res.data);

        } catch (err: any) {
            console.error("Submission failed", err);
            alert("Failed to submit quiz: " + (err.response?.data?.detail || err.message));
        }
    };

    const handleRecoverSignature = async () => {
        try {
            console.log("Attempting to recover signature...");
            const token = await getToken();
            const res = await axios.post(`http://localhost:8000/api/v1/quiz/${quizId}/recover_signature`, {
                wallet_address: address
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });
            console.log("Signature recovered:", res.data);
            setQuiz(res.data);
            if (res.data.signature) {
                // Auto-trigger claim or let user click? Let user click.
                alert("Signature recovered! You can now claim your stake.");
            }
        } catch (error) {
            console.error("Failed to recover signature", error);
            // alert("Failed to recover signature. Please try again.");
        }
    };

    // Auto-recover if passed but no signature
    useEffect(() => {
        if (quiz && quiz.score !== null && quiz.score >= 70 && !quiz.signature && isConnected && address) {
            handleRecoverSignature();
        }
    }, [quiz, isConnected, address]);

    if (!mounted) return null;

    if (!isConnected) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-4">
                <h1 className="text-2xl font-bold mb-6">Connect Wallet to Continue</h1>
                <WalletConnect />
            </div>
        );
    }

    if (loading) return <div className="p-8 text-center">Loading Quiz...</div>;
    if (!quiz) return <div className="p-8 text-center text-red-500">Quiz not found</div>;

    // Show Results if score is present (Passed or Failed)
    if (score !== null || quiz.score !== null) {
        const currentScore = score ?? quiz.score;
        const passed = currentScore >= 70;
        return (
            <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg text-center">
                <h2 className="text-2xl font-bold mb-4">{passed ? 'Congratulations!' : 'Quiz Failed'}</h2>
                <div className="text-4xl font-black mb-4 text-indigo-600">{currentScore}%</div>
                <p className="text-gray-600 mb-6">
                    {passed ? 'You have passed the quiz! Claim your stake back.' : 'You did not meet the passing criteria.'}
                </p>
                {passed && (
                    <div className="space-y-4">
                        {quiz.signature ? (
                            <button
                                onClick={handleClaim}
                                disabled={isPending || isConfirming}
                                className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-bold"
                            >
                                {isPending ? 'Confirm in Wallet...' : isConfirming ? 'Processing Claim...' : 'Claim Stake (0.001 ETH)'}
                            </button>
                        ) : (
                            // Helper for when signature is missing (e.g. older quiz)
                            <p className="text-sm text-yellow-600">Signature pending or not available.</p>
                        )}
                        <button
                            onClick={() => window.location.href = '/dashboard'}
                            className="w-full px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                        >
                            Return to Dashboard
                        </button>
                    </div>
                )}
                {!passed && (
                    <button
                        onClick={() => window.location.href = '/dashboard'}
                        className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300"
                    >
                        Return to Dashboard
                    </button>
                )}
            </div>
        );
    }

    // ...

    // Check if user has staked using on-chain data OR if they supposedly already finished it logic handled above
    if (!hasStakedOnChain && !isConfirmed && !localStakeSuccess) {
        return (
            <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg text-center">
                <div className="mb-4 p-2 bg-yellow-100 text-xs text-left">
                    <p><strong>Debug Info:</strong></p>
                    <p>Connected Address: {address?.slice(0, 6)}...</p>
                    <p>Chain ID: {chainId} (Should be 31337)</p>
                    <p>Contract: {CONTRACT_ADDRESS.slice(0, 6)}...</p>
                    <p>Contract Balance: {'0'} ETH</p>
                </div>
                <h2 className="text-xl font-bold mb-4">Stake to Start</h2>
                <p className="text-gray-600 mb-6">
                    You must stake <strong>0.001 ETH</strong> to attempt this quiz.
                    <br />Pass (&gt;70%) to get it back!
                </p>
                <button
                    onClick={handleStake}
                    disabled={isPending || isConfirming}
                    className="w-full py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                    {isPending ? 'Confirm in Wallet...' : isConfirming ? 'Staking...' : 'Stake 0.001 ETH'}
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto p-4 sm:p-6 lg:p-8">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-gray-900">Quiz: {quizId.slice(0, 8)}...</h1>
                <div className="text-sm font-medium text-gray-500">Attempt 1/3</div>
            </div>

            <div className="space-y-8">
                {quiz.questions?.map((q: any, idx: number) => (
                    <div key={q.question_id || idx} className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">{idx + 1}. {q.question_text}</h3>
                        <div className="space-y-3">
                            {q.options.map((opt: string, optIdx: number) => (
                                <label
                                    key={optIdx}
                                    className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${answers[q.question_id] === optIdx ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
                                        }`}
                                >
                                    <input
                                        type="radio"
                                        name={q.question_id}
                                        className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                                        checked={answers[q.question_id] === optIdx}
                                        onChange={() => setAnswers(prev => ({ ...prev, [q.question_id]: optIdx }))}
                                    />
                                    <span className="ml-3 text-gray-700">{opt}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            <div className="mt-8 flex justify-end">
                <button
                    onClick={handleSubmit}
                    className="px-8 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 shadow-lg"
                >
                    Submit Answers
                </button>
            </div>
        </div>
    );
}
