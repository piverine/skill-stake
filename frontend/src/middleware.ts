import { authMiddleware } from '@clerk/nextjs'

export default authMiddleware({
  // Routes that can be accessed while signed out
  publicRoutes: [
    '/',
    '/sign-in(.*)',
    '/sign-up(.*)',
    '/api/health'
  ],
  // Routes that require authentication
  protectedRoutes: [
    '/dashboard(.*)',
    '/upload(.*)',
    '/quiz(.*)',
    '/stakes(.*)'
  ]
})

export const config = {
  matcher: ["/((?!.+\\.[\\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
};