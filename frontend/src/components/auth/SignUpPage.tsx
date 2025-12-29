'use client'

import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Join Skill-Stake
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Start your blockchain-incentivized learning journey
          </p>
        </div>
        <SignUp 
          appearance={{
            elements: {
              formButtonPrimary: 'bg-blue-600 hover:bg-blue-700 text-sm normal-case',
            },
          }}
          redirectUrl="/dashboard"
        />
      </div>
    </div>
  )
}