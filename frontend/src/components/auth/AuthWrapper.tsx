'use client'

import { useAuth, useUser } from '@clerk/nextjs'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface AuthWrapperProps {
  children: React.ReactNode
  requireAuth?: boolean
}

export default function AuthWrapper({ children, requireAuth = false }: AuthWrapperProps) {
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    const handleAuth = async () => {
      if (isLoaded) {
        if (requireAuth && !isSignedIn) {
          router.push('/sign-in')
          return
        }

        if (isSignedIn) {
          try {
            const jwtToken = await getToken()
            setToken(jwtToken)
            
            // Store token in localStorage for API calls
            if (jwtToken) {
              localStorage.setItem('clerk_token', jwtToken)
            }
          } catch (error) {
            console.error('Error getting token:', error)
          }
        }
      }
    }

    handleAuth()
  }, [isLoaded, isSignedIn, getToken, requireAuth, router])

  // Show loading state while Clerk is initializing
  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  // If auth is required but user is not signed in, don't render children
  if (requireAuth && !isSignedIn) {
    return null
  }

  return <>{children}</>
}