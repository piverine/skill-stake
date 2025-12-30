"use client";

import { useEffect, useState } from 'react';
import { useAuth, useUser } from '@clerk/nextjs';
import axios from 'axios';
import Link from 'next/link';
import { format } from 'date-fns';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Play, CheckCircle2, Clock, BarChart3, TrendingUp, BookOpen, AlertCircle } from 'lucide-react';
import clsx from 'clsx';

interface Quiz {
  quiz_id: string;
  source_material: string;
  score: number | null;
  is_passed: boolean | null;
  created_at: string;
  completed_at: string | null;
}

export default function Dashboard() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'active' | 'history'>('active');

  useEffect(() => {
    const fetchQuizzes = async () => {
      if (!isLoaded || !isSignedIn) return;

      try {
        const token = await getToken();
        const res = await axios.get('http://localhost:8000/api/v1/quiz/user/quizzes', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setQuizzes(res.data);
      } catch (error) {
        console.error("Failed to fetch quizzes", error);
      } finally {
        setLoading(false);
      }
    };

    fetchQuizzes();
  }, [isLoaded, isSignedIn, getToken]);

  if (!isLoaded) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-indigo-600"></div>
    </div>
  );

  if (!isSignedIn) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-gray-50 dark:bg-gray-950">
        <h1 className="text-2xl font-bold">Please Sign In</h1>
        <Link href="/" className="px-6 py-2 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 transition">
          Go Home
        </Link>
      </div>
    );
  }

  const activeQuizzes = quizzes.filter(q => !q.completed_at);
  const completedQuizzes = quizzes.filter(q => q.completed_at);

  // Stats
  const totalCompleted = completedQuizzes.length;
  const totalPassed = completedQuizzes.filter(q => q.is_passed).length;
  const passRate = totalCompleted > 0 ? Math.round((totalPassed / totalCompleted) * 100) : 0;
  const totalEarned = totalPassed * 0.001; // Estimate

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 p-4 sm:p-8">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* Header & Stats */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-6"
        >
          <div className="md:col-span-1">
            <h1 className="text-3xl font-bold mb-2">Welcome back,</h1>
            <p className="text-gray-500 text-lg truncate">{user?.firstName || 'Scholar'}</p>
          </div>

          <StatCard icon={<BookOpen className="text-blue-500" />} label="Quizzes Taken" value={totalCompleted} delay={0.1} />
          <StatCard icon={<TrendingUp className="text-green-500" />} label="Pass Rate" value={`${passRate}%`} delay={0.2} />
          <StatCard icon={<CheckCircle2 className="text-indigo-500" />} label="Est. Earned" value={`${totalEarned.toFixed(3)} ETH`} delay={0.3} />
        </motion.div>

        {/* Action Area */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <Link href="/upload">
            <div className="group border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer hover:border-indigo-500 dark:hover:border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 transition-all">
              <div className="bg-indigo-100 dark:bg-indigo-900/50 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform">
                <Upload className="w-8 h-8 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Upload New Study Material</h3>
              <p className="text-gray-500 max-w-md">Drag & drop your PDF lecture notes or reading material here to generate a new high-stakes quiz.</p>
            </div>
          </Link>
        </motion.div>

        {/* Tabs */}
        <div>
          <div className="flex gap-6 border-b border-gray-200 dark:border-gray-800 mb-6">
            <button
              onClick={() => setActiveTab('active')}
              className={clsx(
                "pb-3 text-lg font-medium transition-colors relative",
                activeTab === 'active' ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              )}
            >
              Active Quizzes ({activeQuizzes.length})
              {activeTab === 'active' && <motion.div layoutId="underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600" />}
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={clsx(
                "pb-3 text-lg font-medium transition-colors relative",
                activeTab === 'history' ? "text-indigo-600 dark:text-indigo-400" : "text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              )}
            >
              History
              {activeTab === 'history' && <motion.div layoutId="underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600" />}
            </button>
          </div>

          <AnimatePresence mode='wait'>
            {activeTab === 'active' ? (
              <motion.div
                key="active"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="grid md:grid-cols-2 gap-4"
              >
                {loading ? (
                  [1, 2].map(i => <SkeletonCard key={i} />)
                ) : activeQuizzes.length === 0 ? (
                  <div className="md:col-span-2 text-center py-12 text-gray-500 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
                    <Clock className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p>No active quizzes. Upload material to start.</p>
                  </div>
                ) : (
                  activeQuizzes.map(quiz => (
                    <Link key={quiz.quiz_id} href={`/quiz/${quiz.quiz_id}`}>
                      <div className="group bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 hover:border-indigo-500 dark:hover:border-indigo-500 hover:shadow-lg transition-all cursor-pointer flex justify-between items-center">
                        <div>
                          <h3 className="font-semibold text-lg mb-1 group-hover:text-indigo-600 transition-colors">{quiz.source_material}</h3>
                          <p className="text-sm text-gray-500 flex items-center gap-2">
                            <Clock className="w-3 h-3" />
                            Created {new Date(quiz.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="bg-indigo-50 dark:bg-indigo-900/30 p-3 rounded-full group-hover:bg-indigo-600 group-hover:text-white transition-all text-indigo-600 dark:text-indigo-400">
                          <Play className="w-5 h-5 fill-current" />
                        </div>
                      </div>
                    </Link>
                  ))
                )}
              </motion.div>
            ) : (
              <motion.div
                key="history"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                {completedQuizzes.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
                    <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-20" />
                    <p>No history yet. Complete a quiz to see stats.</p>
                  </div>
                ) : (
                  completedQuizzes.map((quiz, i) => (
                    <motion.div
                      key={quiz.quiz_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <Link href={`/quiz/${quiz.quiz_id}`}>
                        <div className="bg-white dark:bg-gray-900 p-5 rounded-xl border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={clsx(
                              "w-10 h-10 rounded-full flex items-center justify-center",
                              quiz.is_passed ? "bg-green-100 text-green-600" : "bg-red-100 text-red-600"
                            )}>
                              {quiz.is_passed ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                            </div>
                            <div>
                              <h3 className="font-semibold">{quiz.source_material}</h3>
                              <p className="text-sm text-gray-500">{format(new Date(quiz.completed_at!), 'MMM d, yyyy')}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={clsx("font-bold text-lg", quiz.is_passed ? "text-green-600" : "text-gray-500")}>
                              {quiz.score}%
                            </p>
                            <p className="text-xs text-gray-400 capitalize">{quiz.is_passed ? 'Passed' : 'Failed'}</p>
                          </div>
                        </div>
                      </Link>
                    </motion.div>
                  ))
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, delay }: { icon: React.ReactNode, label: string, value: string | number, delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="bg-white dark:bg-gray-900 p-6 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm"
    >
      <div className="flex items-center gap-4 mb-2">
        <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">{icon}</div>
        <span className="text-gray-500 dark:text-gray-400 font-medium">{label}</span>
      </div>
      <p className="text-3xl font-bold ml-1">{value}</p>
    </motion.div>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 animate-pulse">
      <div className="h-6 bg-gray-200 dark:bg-gray-800 rounded w-3/4 mb-4"></div>
      <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2"></div>
    </div>
  )
}