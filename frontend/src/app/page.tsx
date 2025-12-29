import { SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs'
import Link from 'next/link'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto  lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
          Skill-Stake Learning Platform
        </p>
        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-white via-white dark:from-black dark:via-black lg:static lg:h-auto lg:w-auto lg:bg-none">
          <SignedOut>
            <div className="flex gap-4">
              <SignInButton mode="modal">
                <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                  Sign In
                </button>
              </SignInButton>
              <Link href="/sign-up">
                <button className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
                  Sign Up
                </button>
              </Link>
            </div>
          </SignedOut>
          <SignedIn>
            <div className="flex items-center gap-4">
              <Link href="/dashboard">
                <button className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
                  Dashboard
                </button>
              </Link>
              <UserButton afterSignOutUrl="/" />
            </div>
          </SignedIn>
        </div>
      </div>

      <div className="relative flex place-items-center before:absolute before:h-[300px] before:w-[480px] before:-translate-x-1/2 before:rounded-full before:bg-gradient-radial before:from-white before:to-transparent before:blur-2xl before:content-[''] after:absolute after:-z-20 after:h-[180px] after:w-[240px] after:translate-x-1/3 after:bg-gradient-conic after:from-sky-200 after:via-blue-200 after:blur-2xl after:content-[''] before:dark:bg-gradient-to-br before:dark:from-transparent before:dark:to-blue-700 before:dark:opacity-10 after:dark:from-sky-900 after:dark:via-[#0141ff] after:dark:opacity-40 before:lg:h-[360px] z-[-1]">
        <h1 className="text-4xl font-bold text-center">
          Welcome to Skill-Stake
        </h1>
      </div>

      <div className="mb-32 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-4 lg:text-left">
        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
          <h2 className="mb-3 text-2xl font-semibold">
            Upload Study Material
          </h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Upload PDF documents to generate AI-powered quizzes
          </p>
        </div>

        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
          <h2 className="mb-3 text-2xl font-semibold">
            Stake ETH
          </h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Put your money where your learning is - stake ETH to take quizzes
          </p>
        </div>

        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
          <h2 className="mb-3 text-2xl font-semibold">
            Take Quiz
          </h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Answer AI-generated questions based on your study materials
          </p>
        </div>

        <div className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30">
          <h2 className="mb-3 text-2xl font-semibold">
            Get Results
          </h2>
          <p className="m-0 max-w-[30ch] text-sm opacity-50">
            Score 70%+ to get your stake back, otherwise it goes to charity
          </p>
        </div>
      </div>
    </main>
  )
}