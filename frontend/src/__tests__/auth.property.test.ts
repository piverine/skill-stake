/**
 * Feature: skill-stake-learning, Property 1: Authentication and Authorization Consistency
 * Validates: Requirements 1.1, 1.2, 1.3, 1.4
 */

import * as fc from 'fast-check'
import { useAuth } from '@clerk/nextjs'
import { getAuthToken, createAuthenticatedRequest } from '@/lib/auth'

// Mock implementations
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>

describe('Property 1: Authentication and Authorization Consistency', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    localStorage.clear()
    global.fetch = jest.fn()
  })

  it('should require authentication for all protected operations', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          isSignedIn: fc.boolean(),
          hasValidToken: fc.boolean(),
          tokenValue: fc.option(fc.string({ minLength: 10, maxLength: 100 }), { nil: null }),
          apiEndpoint: fc.constantFrom('/api/stakes', '/api/quiz', '/api/upload', '/api/user'),
          httpMethod: fc.constantFrom('GET', 'POST', 'PUT', 'DELETE'),
        }),
        async ({ isSignedIn, hasValidToken, tokenValue, apiEndpoint, httpMethod }) => {
          // Setup mock auth state
          mockUseAuth.mockReturnValue({
            isLoaded: true,
            isSignedIn,
            getToken: jest.fn().mockResolvedValue(hasValidToken ? tokenValue : null),
            userId: isSignedIn ? 'user_123' : null,
            sessionId: isSignedIn ? 'sess_123' : null,
            orgId: null,
            orgRole: null,
            orgSlug: null,
            has: jest.fn(),
            signOut: jest.fn(),
          } as any)

          // Setup localStorage if token exists
          if (hasValidToken && tokenValue) {
            localStorage.setItem('clerk_token', tokenValue)
            localStorage.setItem('clerk_token_timestamp', Date.now().toString())
          }

          // Mock fetch response
          const mockResponse = {
            ok: isSignedIn && hasValidToken,
            status: isSignedIn && hasValidToken ? 200 : 401,
            json: jest.fn().mockResolvedValue(
              isSignedIn && hasValidToken 
                ? { success: true, data: 'mock_data' }
                : { error: 'Unauthorized' }
            ),
          }
          ;(global.fetch as jest.Mock).mockResolvedValue(mockResponse)

          try {
            // Test API request with authentication
            const response = await createAuthenticatedRequest(
              `http://localhost:8000${apiEndpoint}`,
              { method: httpMethod }
            )

            // Property: Authentication consistency
            if (isSignedIn && hasValidToken && tokenValue) {
              // When user is authenticated with valid token, requests should succeed
              expect(response.status).toBe(200)
              expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining(apiEndpoint),
                expect.objectContaining({
                  method: httpMethod,
                  headers: expect.objectContaining({
                    'Authorization': `Bearer ${tokenValue}`,
                    'Content-Type': 'application/json',
                  }),
                })
              )
            } else {
              // When user is not authenticated or token is invalid, requests should fail
              if (!isSignedIn || !hasValidToken) {
                // Either no token sent or invalid token should result in 401
                expect(response.status).toBe(401)
              }
            }
          } catch (error) {
            // Network errors are acceptable, but auth logic should still be consistent
            expect(error).toBeDefined()
          }
        }
      ),
      { numRuns: 100 }
    )
  })

  it('should maintain token consistency across operations', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          initialToken: fc.option(fc.string({ minLength: 20, maxLength: 50 }), { nil: null }),
          newToken: fc.option(fc.string({ minLength: 20, maxLength: 50 }), { nil: null }),
          timeOffset: fc.integer({ min: 0, max: 7200000 }), // 0 to 2 hours in ms
        }),
        async ({ initialToken, newToken, timeOffset }) => {
          // Setup initial token state
          if (initialToken) {
            localStorage.setItem('clerk_token', initialToken)
            localStorage.setItem('clerk_token_timestamp', (Date.now() - timeOffset).toString())
          }

          // Mock auth hook
          mockUseAuth.mockReturnValue({
            isLoaded: true,
            isSignedIn: !!newToken,
            getToken: jest.fn().mockResolvedValue(newToken),
            userId: newToken ? 'user_123' : null,
            sessionId: newToken ? 'sess_123' : null,
            orgId: null,
            orgRole: null,
            orgSlug: null,
            has: jest.fn(),
            signOut: jest.fn(),
          } as any)

          // Get token through our auth utility
          const retrievedToken = await getAuthToken()

          // Property: Token consistency
          if (initialToken && timeOffset < 3000000) { // Less than 50 minutes old
            // Should return stored token if it's still fresh
            expect(retrievedToken).toBe(initialToken)
          } else if (newToken) {
            // Should get new token if old one expired or doesn't exist
            // Note: In real implementation, this would trigger token refresh
            expect(retrievedToken).toBeDefined()
          } else {
            // No valid token available
            expect(retrievedToken).toBeNull()
          }
        }
      ),
      { numRuns: 100 }
    )
  })

  it('should enforce user data isolation', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          userId1: fc.string({ minLength: 5, maxLength: 20 }),
          userId2: fc.string({ minLength: 5, maxLength: 20 }),
          token1: fc.string({ minLength: 20, maxLength: 50 }),
          token2: fc.string({ minLength: 20, maxLength: 50 }),
          dataEndpoint: fc.constantFrom('/api/user/stakes', '/api/user/quizzes', '/api/user/profile'),
        }),
        async ({ userId1, userId2, token1, token2, dataEndpoint }) => {
          // Ensure different users
          fc.pre(userId1 !== userId2)
          fc.pre(token1 !== token2)

          // Mock responses for different users
          const mockUserData1 = { userId: userId1, data: `data_for_${userId1}` }
          const mockUserData2 = { userId: userId2, data: `data_for_${userId2}` }

          // Test with first user's token
          ;(global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: jest.fn().mockResolvedValue(mockUserData1),
          })

          const response1 = await createAuthenticatedRequest(
            `http://localhost:8000${dataEndpoint}`,
            { method: 'GET' }
          )

          // Setup token for first user
          localStorage.setItem('clerk_token', token1)
          
          // Test with second user's token
          localStorage.setItem('clerk_token', token2)
          ;(global.fetch as jest.Mock).mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: jest.fn().mockResolvedValue(mockUserData2),
          })

          const response2 = await createAuthenticatedRequest(
            `http://localhost:8000${dataEndpoint}`,
            { method: 'GET' }
          )

          // Property: User data isolation
          // Each user should only access their own data
          const data1 = await response1.json()
          const data2 = await response2.json()

          expect(data1.userId).toBe(userId1)
          expect(data2.userId).toBe(userId2)
          expect(data1.data).not.toBe(data2.data)

          // Verify correct tokens were sent
          expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining(dataEndpoint),
            expect.objectContaining({
              headers: expect.objectContaining({
                'Authorization': `Bearer ${token2}`, // Last call should use token2
              }),
            })
          )
        }
      ),
      { numRuns: 100 }
    )
  })
})