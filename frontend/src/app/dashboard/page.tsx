'use client'

import { useUser } from '@clerk/nextjs'
import AuthWrapper from '@/components/auth/AuthWrapper'
import Link from 'next/link'

export default function Dashboard() {
  const { user } = useUser()

  return (
    <AuthWrapper requireAuth={true}>
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-4">
                Welcome to your Dashboard, {user?.firstName || 'User'}!
              </h1>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-blue-50 p-6 rounded-lg">
                  <h3 className="text-lg font-medium text-blue-900 mb-2">
                    Upload Study Material
                  </h3>
                  <p className="text-blue-700 text-sm">
                    Upload PDF documents to generate AI-powered quizzes
                  </p>
                  <Link href="/upload" className="mt-4 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 inline-block">
                    Upload PDF
                  </Link>
                </div>

                <div className="bg-green-50 p-6 rounded-lg">
                  <h3 className="text-lg font-medium text-green-900 mb-2">
                    Active Stakes
                  </h3>
                  <p className="text-green-700 text-sm">
                    View and manage your current ETH stakes
                  </p>
                  <button className="mt-4 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                    View Stakes
                  </button>
                </div>

                <div className="bg-purple-50 p-6 rounded-lg">
                  <h3 className="text-lg font-medium text-purple-900 mb-2">
                    Quiz History
                  </h3>
                  <p className="text-purple-700 text-sm">
                    Review your past quiz results and scores
                  </p>
                  <button className="mt-4 bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700">
                    View History
                  </button>
                </div>
              </div>

              <div className="mt-8 bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Account Information
                </h3>
                <div className="text-sm text-gray-600">
                  <p><strong>Email:</strong> {user?.emailAddresses[0]?.emailAddress}</p>
                  <p><strong>User ID:</strong> {user?.id}</p>
                  <p><strong>Member since:</strong> {user?.createdAt?.toLocaleDateString()}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AuthWrapper>
  )
}