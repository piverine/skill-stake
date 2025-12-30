'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useAccount, useWriteContract, useReadContract, useWaitForTransactionReceipt, useBalance } from 'wagmi';
import { parseEther, keccak256, toHex } from 'viem';
import { WalletConnect } from '@/components/WalletConnect';
import axios from 'axios';
import { useAuth } from '@clerk/nextjs';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, ShieldCheck, AlertCircle, Coins, ArrowRight, CheckCircle2, XCircle, Wallet } from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs));
}

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

// Replace with deployed address
const CONTRACT_ADDRESS = "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82";

export default function QuizPage() {
    const params = useParams();
    const quizId = params.id as string;
    const { address, isConnected, chainId } = useAccount();
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
    }, [quizId, isLoaded, isSignedIn]);

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
            const token = await getToken();

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
            <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="text-center bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-xl max-w-md w-full"
                >
                    <Wallet className="w-16 h-16 mx-auto mb-4 text-indigo-500" />
                    <h1 className="text-2xl font-bold mb-2">Connect Wallet</h1>
                    <p className="text-gray-500 mb-6">Connect your wallet to start staking and quizzing.</p>
                    <div className="flex justify-center">
                        <WalletConnect />
                    </div>
                </motion.div>
            </div>
        );
    }

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600"></div>
        </div>
    );

    if (!quiz) return (
        <div className="min-h-screen flex items-center justify-center text-red-500">
            <AlertCircle className="w-6 h-6 mr-2" /> Quiz not found
        </div>
    );

    // Show Results if score is present (Passed or Failed)
    if (score !== null || quiz.score !== null) {
        const currentScore = score ?? quiz.score;
        const passed = currentScore >= 70;
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
                <motion.div
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    className="max-w-md w-full bg-white dark:bg-gray-800 rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-gray-700"
                >
                    <div className={cn(
                        "p-8 text-center bg-gradient-to-b",
                        passed ? "from-green-50 to-white dark:from-green-900/20 dark:to-gray-800" : "from-red-50 to-white dark:from-red-900/20 dark:to-gray-800"
                    )}>
                        <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 200, damping: 10 }}
                            className={cn(
                                "w-24 h-24 mx-auto rounded-full flex items-center justify-center mb-4 shadow-lg",
                                passed ? "bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400" : "bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400"
                            )}
                        >
                            {passed ? <Trophy className="w-12 h-12" /> : <XCircle className="w-12 h-12" />}
                        </motion.div>

                        <h2 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">{passed ? 'Excellent!' : 'Keep Trying!'}</h2>
                        <div className="text-5xl font-black mb-4 text-indigo-600 dark:text-indigo-400 tracking-tighter">{currentScore}%</div>
                        <p className="text-gray-600 dark:text-gray-300 mb-8 leading-relaxed">
                            {passed ? 'You demonstrated mastery of the material. Your stake is ready for withdrawal.' : 'Review your study material and try again to reclaim your stake.'}
                        </p>

                        {passed && (
                            <div className="space-y-3">
                                {quiz.signature ? (
                                    <button
                                        onClick={handleClaim}
                                        disabled={isPending || isConfirming}
                                        className="w-full px-6 py-4 bg-green-600 text-white rounded-xl hover:bg-green-700 font-bold shadow-lg hover:shadow-green-500/30 transition-all flex items-center justify-center gap-2"
                                    >
                                        {isPending ? 'Confirming...' : isConfirming ? 'Processing...' : (
                                            <>
                                                <Coins className="w-5 h-5" />
                                                Claim 0.001 ETH Refund
                                            </>
                                        )}
                                    </button>
                                ) : (
                                    <p className="text-sm text-yellow-600 bg-yellow-50 p-2 rounded">Signature verification pending...</p>
                                )}
                            </div>
                        )}

                        <button
                            onClick={() => window.location.href = '/dashboard'}
                            className="mt-4 w-full px-6 py-4 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-200 dark:hover:bg-gray-600 font-medium transition-colors"
                        >
                            Return to Dashboard
                        </button>
                    </div>
                </motion.div>
            </div>
        );
    }

    // Check if user has staked using on-chain data OR if they supposedly already finished
    if (!hasStakedOnChain && !isConfirmed && !localStakeSuccess) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="max-w-md w-full bg-white dark:bg-gray-800 rounded-3xl shadow-xl p-8 border border-gray-200 dark:border-gray-700 relative overflow-hidden"
                >
                    <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl -mr-16 -mt-16 pointer-events-none" />

                    <div className="mb-6 p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-xl border border-indigo-100 dark:border-indigo-800/50">
                        <h3 className="text-xs font-bold text-indigo-800 dark:text-indigo-300 uppercase tracking-wider mb-2">Debug Info</h3>
                        <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-gray-400 font-mono">
                            <span>Chain ID:</span> <span>{chainId} (Req: 31337)</span>
                            <span>Contract:</span> <span title={CONTRACT_ADDRESS}>{CONTRACT_ADDRESS.slice(0, 6)}...</span>
                        </div>
                    </div>

                    <div className="text-center mb-8">
                        <div className="bg-gradient-to-br from-indigo-500 to-purple-600 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg rotate-3">
                            <ShieldCheck className="text-white w-8 h-8" />
                        </div>
                        <h2 className="text-2xl font-bold mb-2">Commit to Start</h2>
                        <p className="text-gray-600 dark:text-gray-400">
                            Stake <strong>0.001 ETH</strong> to prove your confidence.
                            <br />Pass the quiz with &gt;70% to instantly refund it.
                        </p>
                    </div>

                    <button
                        onClick={handleStake}
                        disabled={isPending || isConfirming}
                        className="w-full py-4 bg-indigo-600 text-white rounded-xl font-bold text-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-indigo-500/25 transition-all flex items-center justify-center gap-2"
                    >
                        {isPending ? 'Confirm in Wallet...' : isConfirming ? (
                            <><div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" /> Staking...</>
                        ) : (
                            <>Stake & Start Quiz <ArrowRight className="w-5 h-5" /></>
                        )}
                    </button>
                    {!isOnLocalNetwork(chainId) && (
                        <p className="mt-4 text-xs text-red-500 text-center bg-red-50 p-2 rounded">
                            Wrong Network. Switch to Localhost 8545.
                        </p>
                    )}
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 dark:bg-gray-950 py-12 px-4 sm:px-6">
            <div className="max-w-3xl mx-auto">
                <header className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Quiz Session</h1>
                        <p className="text-sm text-gray-500">{quizId.slice(0, 8)}...</p>
                    </div>
                    <div className="px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm font-medium border border-gray-200 dark:border-gray-700">
                        {Object.keys(answers).length} / {quiz.questions?.length} Answered
                    </div>
                </header>

                <div className="space-y-6">
                    <AnimatePresence mode='wait'>
                        {quiz.questions?.map((q: any, idx: number) => (
                            <motion.div
                                key={q.question_id || idx}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: idx * 0.1 }}
                                className="bg-white dark:bg-gray-900 p-8 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-800 relative overflow-hidden group hover:shadow-md transition-shadow"
                            >
                                <div className="absolute top-0 left-0 w-1 h-full bg-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity" />

                                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-6 flex gap-3">
                                    <span className="flex-shrink-0 w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-sm font-bold">
                                        {idx + 1}
                                    </span>
                                    {q.question_text}
                                </h3>

                                <div className="space-y-3 pl-11">
                                    {q.options.map((opt: string, optIdx: number) => {
                                        const isSelected = answers[q.question_id] === optIdx;
                                        return (
                                            <label
                                                key={optIdx}
                                                className={cn(
                                                    "flex items-center p-4 rounded-xl cursor-pointer transition-all border-2",
                                                    isSelected
                                                        ? "border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 dark:border-indigo-500"
                                                        : "border-transparent bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700"
                                                )}
                                            >
                                                <div className="relative flex items-center justify-center">
                                                    <input
                                                        type="radio"
                                                        name={q.question_id}
                                                        className="peer appearance-none h-5 w-5 border-2 border-gray-300 rounded-full checked:border-indigo-600 checked:bg-indigo-600 transition-all"
                                                        checked={isSelected}
                                                        onChange={() => setAnswers(prev => ({ ...prev, [q.question_id]: optIdx }))}
                                                    />
                                                    <div className="absolute w-2 h-2 bg-white rounded-full opacity-0 peer-checked:opacity-100 pointer-events-none" />
                                                </div>
                                                <span className={cn(
                                                    "ml-3 text-gray-700 dark:text-gray-300 font-medium",
                                                    isSelected && "text-indigo-900 dark:text-indigo-100"
                                                )}>
                                                    {opt}
                                                </span>
                                            </label>
                                        );
                                    })}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>

                <div className="mt-10 flex justify-end sticky bottom-6 z-10">
                    <button
                        onClick={handleSubmit}
                        className="px-10 py-4 bg-indigo-600 text-white font-bold text-lg rounded-full hover:bg-indigo-700 focus:outline-none focus:ring-4 focus:ring-indigo-500/30 shadow-xl hover:shadow-indigo-600/40 hover:-translate-y-1 transition-all active:translate-y-0"
                    >
                        Submit All Answers
                    </button>
                </div>
            </div>
        </div>
    );
}

function isOnLocalNetwork(chainId: number | undefined) {
    return chainId === 31337;
}
