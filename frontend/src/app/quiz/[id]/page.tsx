'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAccount, useWriteContract, useReadContract, useWaitForTransactionReceipt } from 'wagmi';
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
    }
];

// Replace with deployed address (Dummy for now)
const CONTRACT_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3";

export default function QuizPage() {
    const params = useParams();
    const quizId = params.id as string;
    const { address, isConnected } = useAccount();
    const { getToken, isLoaded, isSignedIn } = useAuth();

    const [quiz, setQuiz] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [answers, setAnswers] = useState<Record<string, number>>({});
    const [score, setScore] = useState<number | null>(null);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    // Wagmi Hooks
    const { writeContract, data: hash, isPending: isStaking } = useWriteContract();
    const { isLoading: isConfirming, isSuccess: isConfirmed } = useWaitForTransactionReceipt({ hash });

    // Convert quiz UUID string to bytes32 for contract using keccak256 hash
    // UUID string is too long for bytes32 direct conversion
    const quizIdBytes32 = keccak256(toHex(quizId));

    // Check if user has staked
    const { data: hasStakedOnChain } = useReadContract({
        address: CONTRACT_ADDRESS,
        abi: CONTRACT_ABI,
        functionName: 'hasStaked',
        args: [quizIdBytes32, address as `0x${string}`],
    });

    useEffect(() => {
        console.log("Staked on chain?", hasStakedOnChain);
    }, [hasStakedOnChain]);

    useEffect(() => {
        if (!isLoaded) return;

        console.log("QuizPage mounted. ID:", quizId);

        // Fetch Quiz Data
        const fetchQuiz = async () => {
            console.log("Starting fetchQuiz...");
            // Add a timeout to prevent infinite hanging
            const timeoutId = setTimeout(() => {
                if (loading) {
                    console.error("Fetch timed out");
                    setLoading(false);
                    // could set an error state here
                }
            }, 10000);

            try {
                if (!isSignedIn) {
                    console.warn("User not signed in, skipping fetch");
                    setLoading(false);
                    return;
                }

                console.log("Getting token...");
                const token = await getToken();
                console.log("Token received:", token ? "YES" : "NO");

                console.log("Fetching quiz from API...");
                const res = await axios.get(`http://localhost:8000/api/v1/quiz/${quizId}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                console.log("Quiz data received:", res.data);
                setQuiz(res.data);
            } catch (err) {
                console.error("Failed to load quiz", err);
            } finally {
                clearTimeout(timeoutId);
                console.log("Setting loading false");
                setLoading(false);
            }
        };

        if (quizId) {
            fetchQuiz();
        } else {
            console.warn("No quizId found in params:", params);
            setLoading(false);
        }
    }, [quizId, getToken, params, isLoaded, isSignedIn]);

    useEffect(() => {
        // ... previous useEffect logic
        if (quiz) {
            // Check if user already passed
            if (quiz.score !== null) {
                setScore(quiz.score);
            }
        }
    }, [quiz]);

    const handleClaim = async () => {
        if (!quiz?.signature) {
            alert("No signature found. Cannot claim.");
            return;
        }
        try {
            await writeContract({
                address: CONTRACT_ADDRESS,
                abi: [
                    ...CONTRACT_ABI,
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
                ],
                functionName: 'withdraw',
                args: [quizIdBytes32, quiz.signature as `0x${string}`],
            });
        } catch (error) {
            console.error("Claim failed:", error);
            alert("Failed to claim stake.");
        }
    };

    const handleStake = async () => {
        try {
            console.log("Initiating stake for quiz:", quizId);
            console.log("Quiz ID Bytes32:", quizIdBytes32);
            await writeContract({
                address: CONTRACT_ADDRESS,
                abi: CONTRACT_ABI,
                functionName: 'stake',
                args: [quizIdBytes32],
                value: parseEther('0.01'),
            });
        } catch (error) {
            console.error("Staking failed:", error);
            alert("Failed to initiate staking. Check console for details.");
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
                                {isPending ? 'Confirm in Wallet...' : isConfirming ? 'Processing Claim...' : 'Claim Stake (0.01 ETH)'}
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

    // Check if user has staked using on-chain data OR if they supposedly already finished it logic handled above
    if (!hasStakedOnChain && !isConfirmed) {
        return (
            <div className="max-w-md mx-auto mt-10 p-6 bg-white rounded-lg shadow-lg text-center">
                <h2 className="text-xl font-bold mb-4">Stake to Start</h2>
                <p className="text-gray-600 mb-6">
                    You must stake <strong>0.01 ETH</strong> to attempt this quiz.
                    <br />Pass (>70%) to get it back!
                </p>
                <button
                    onClick={handleStake}
                    disabled={isStaking || isConfirming}
                    className="w-full py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                    {isStaking ? 'Confirm in Wallet...' : isConfirming ? 'Staking...' : 'Stake 0.01 ETH'}
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
