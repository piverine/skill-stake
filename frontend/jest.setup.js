import '@testing-library/jest-dom'

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
global.localStorage = localStorageMock

// Mock fetch
global.fetch = jest.fn()

// Mock Clerk
jest.mock('@clerk/nextjs', () => ({
  useAuth: jest.fn(),
  useUser: jest.fn(),
  SignIn: jest.fn(() => <div data-testid="sign-in">SignIn Component</div>),
  SignUp: jest.fn(() => <div data-testid="sign-up">SignUp Component</div>),
  SignInButton: jest.fn(({ children }) => <button data-testid="sign-in-button">{children}</button>),
  SignedIn: jest.fn(({ children }) => <div data-testid="signed-in">{children}</div>),
  SignedOut: jest.fn(({ children }) => <div data-testid="signed-out">{children}</div>),
  UserButton: jest.fn(() => <button data-testid="user-button">User</button>),
  ClerkProvider: jest.fn(({ children }) => <div data-testid="clerk-provider">{children}</div>),
  authMiddleware: jest.fn(() => (req, res, next) => next()),
}))

// Mock Next.js router
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
  })),
  usePathname: jest.fn(() => '/'),
  useSearchParams: jest.fn(() => new URLSearchParams()),
}))