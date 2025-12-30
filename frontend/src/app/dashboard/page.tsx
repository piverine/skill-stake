"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import axios from 'axios';
import Link from 'next/link';
import { format } from 'date-fns';

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
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);

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

  if (!isLoaded) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;

  if (!isSignedIn) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <h1 className="text-2xl font-bold">Please Sign In</h1>
        <Link href="/" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
          Go Home
        </Link>
      </div>
    );
  }

  const activeQuizzes = quizzes.filter(q => !q.completed_at);
  const completedQuizzes = quizzes.filter(q => q.completed_at);

  return (
    <div className="min-h-screen p-8 bg-gray-50 dark:bg-zinc-900 text-gray-900 dark:text-gray-100">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

        <div className="mb-8 p-6 bg-white dark:bg-zinc-800 rounded-xl shadow-sm border border-gray-200 dark:border-zinc-700">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <Link href="/upload">
            <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">
              Upload New Material
            </button>
          </Link>
        </div>

        <div className="mb-12">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Active Quizzes
          </h2>
          {loading ? (
            <p>Loading...</p>
          ) : activeQuizzes.length === 0 ? (
            <p className="text-gray-500 italic">No active quizzes found.</p>
          ) : (
            <div className="grid gap-4">
              {activeQuizzes.map(quiz => (
                <Link key={quiz.quiz_id} href={`/quiz/${quiz.quiz_id}`}>
                  <div className="p-4 bg-white dark:bg-zinc-800 rounded-lg border border-gray-200 dark:border-zinc-700 hover:border-blue-500 transition cursor-pointer flex justify-between items-center">
                    <div>
                      <h3 className="font-semibold">{quiz.source_material}</h3>
                      <p className="text-sm text-gray-500">Created {new Date(quiz.created_at).toLocaleDateString()}</p>
                    </div>
                    <span className="px-3 py-1 bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200 rounded-full text-sm">
                      Continue
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4 text-gray-600 dark:text-gray-400">History</h2>
          {loading ? (
            <p>Loading...</p>
          ) : completedQuizzes.length === 0 ? (
            <p className="text-gray-500 italic">No completed quizzes yet.</p>
          ) : (
            <div className="grid gap-4">
              {completedQuizzes.map(quiz => (
                <Link key={quiz.quiz_id} href={`/quiz/${quiz.quiz_id}`}>
                  <div className="p-4 bg-gray-50 dark:bg-zinc-800/50 rounded-lg border border-gray-200 dark:border-zinc-700 flex justify-between items-center opacity-75 hover:opacity-100 transition">
                    <div>
                      <h3 className="font-semibold">{quiz.source_material}</h3>
                      <p className="text-sm text-gray-500">Completed {format(new Date(quiz.completed_at!), 'PPP')}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className={`font-bold ${quiz.is_passed ? 'text-green-600' : 'text-red-600'}`}>
                        {quiz.score}%
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm ${quiz.is_passed
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                        }`}>
                        {quiz.is_passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}