'use client';

import { SignInButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowRight, BookOpen, Coins, Trophy, GraduationCap, ShieldCheck, Zap } from 'lucide-react'

// Animation variants
const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } }
}

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2
    }
  }
}

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-950 dark:to-gray-900 text-gray-900 dark:text-gray-100 overflow-x-hidden">

      {/* Navigation */}
      <nav className="fixed w-full z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-1.5 rounded-lg">
              <GraduationCap className="h-6 w-6 text-white" />
            </div>
            <span className="font-bold text-xl tracking-tight">Skill-Stake</span>
          </div>

          <div className="flex items-center gap-4">
            <SignedOut>
              <SignInButton mode="modal">
                <button className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium transition-colors">
                  Sign In
                </button>
              </SignInButton>
              <Link href="/sign-up">
                <button className="bg-indigo-600 text-white px-5 py-2 rounded-full hover:bg-indigo-700 transition-all font-medium shadow-md hover:shadow-indigo-500/20">
                  Get Started
                </button>
              </Link>
            </SignedOut>
            <SignedIn>
              <Link href="/dashboard">
                <button className="text-gray-600 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 font-medium mr-4">
                  Dashboard
                </button>
              </Link>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 px-4 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-7xl z-0 pointer-events-none">
          <div className="absolute top-20 left-10 w-72 h-72 bg-purple-300 dark:bg-purple-900 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob" />
          <div className="absolute top-20 right-10 w-72 h-72 bg-indigo-300 dark:bg-indigo-900 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000" />
          <div className="absolute -bottom-8 left-1/2 w-72 h-72 bg-pink-300 dark:bg-pink-900 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000" />
        </div>

        <motion.div
          className="relative z-10 max-w-4xl mx-auto text-center"
          initial="hidden"
          animate="visible"
          variants={staggerContainer}
        >
          <motion.h1
            className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400"
            variants={fadeInUp}
          >
            Learn. Stake. <br /> Prove Your Skill.
          </motion.h1>

          <motion.p
            className="text-xl md:text-2xl text-gray-600 dark:text-gray-300 mb-10 max-w-2xl mx-auto leading-relaxed"
            variants={fadeInUp}
          >
            Turn your study material into high-stakes quizzes.
            Commit ETH to prove your knowledge, and earn it back when you pass.
          </motion.p>

          <motion.div
            className="flex flex-col sm:flex-row gap-4 justify-center"
            variants={fadeInUp}
          >
            <Link href="/dashboard">
              <button className="w-full sm:w-auto px-8 py-4 bg-indigo-600 text-white rounded-full font-bold text-lg hover:bg-indigo-700 transition-all shadow-lg hover:shadow-indigo-500/25 flex items-center justify-center gap-2 group">
                Start Staking
                <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </Link>
            <Link href="#how-it-works">
              <button className="w-full sm:w-auto px-8 py-4 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-full font-bold text-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-all shadow-sm">
                How It Works
              </button>
            </Link>
          </motion.div>
        </motion.div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-white dark:bg-gray-900/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            className="grid md:grid-cols-3 gap-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={staggerContainer}
          >
            <FeatureCard
              icon={<Zap className="h-8 w-8 text-yellow-500" />}
              title="AI-Powered"
              description="Upload any PDF and let our AI generate challenging quizzes instantly. No manual creation needed."
            />
            <FeatureCard
              icon={<Coins className="h-8 w-8 text-indigo-500" />}
              title="Crypto Staking"
              description="Put skin in the game. Stake ETH to attempt quizzes. Passing is the only way to get your money back."
            />
            <FeatureCard
              icon={<ShieldCheck className="h-8 w-8 text-green-500" />}
              title="Verifiable Proof"
              description="Your success is verified on-chain. Build a verifiable portfolio of your mastered skills."
            />
          </motion.div>
        </div>
      </section>

      {/* Detailed Steps Section */}
      <section id="how-it-works" className="py-24 relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">How It Works</h2>
            <p className="text-gray-600 dark:text-gray-400">Example workflow for a motivated learner.</p>
          </div>

          <div className="grid md:grid-cols-2 gap-12 items-center">
            <motion.div
              className="space-y-8"
              initial={{ opacity: 0, x: -50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <Step
                number="01"
                title="Upload Material"
                desc="Upload your course notes, textbooks, or papers. Our AI processes them in seconds."
              />
              <Step
                number="02"
                title="Stake ETH"
                desc="Commit to learning. Stake 0.001 ETH to unlock the quiz. This ensures you are serious."
              />
              <Step
                number="03"
                title="Pass & Earn"
                desc="Score above 70% to pass. Your stake is refunded automatically via smart contract."
              />
            </motion.div>

            <motion.div
              className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl p-1 shadow-2xl rotate-2 hover:rotate-0 transition-transform duration-500"
              initial={{ opacity: 0, x: 50 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <div className="bg-gray-900 rounded-xl p-6 h-full flex items-center justify-center min-h-[400px]">
                <div className="text-center">
                  <Trophy className="h-20 w-20 text-yellow-400 mx-auto mb-6" />
                  <h3 className="text-2xl font-bold text-white mb-2">Quiz Passed!</h3>
                  <p className="text-indigo-200">0.001 ETH Refunded</p>
                  <div className="mt-8 bg-gray-800 rounded-lg p-4 font-mono text-xs text-left text-green-400">
                    <p>&gt; Verifying answers...</p>
                    <p>&gt; Score: 95%</p>
                    <p>&gt; Smart Contract Interface...</p>
                    <p>&gt; Transaction Confirmed (Block #21)</p>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-50 dark:bg-gray-950 py-12 border-t border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-6 w-6 text-indigo-600" />
            <span className="font-bold text-lg">Skill-Stake</span>
          </div>
          <p className="text-sm text-gray-500">
            © 2024 Skill-Stake Platform. Built for Hackathon.
          </p>
          <div className="flex gap-6">
            <Link href="#" className="text-gray-500 hover:text-indigo-600 transition-colors">Twitter</Link>
            <Link href="#" className="text-gray-500 hover:text-indigo-600 transition-colors">GitHub</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <motion.div
      className="p-8 rounded-2xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-xl transition-shadow"
      variants={fadeInUp}
    >
      <div className="mb-4 bg-gray-50 dark:bg-gray-700/50 w-16 h-16 rounded-xl flex items-center justify-center">
        {icon}
      </div>
      <h3 className="text-xl font-bold mb-3 text-gray-900 dark:text-white">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
        {description}
      </p>
    </motion.div>
  )
}

function Step({ number, title, desc }: { number: string, title: string, desc: string }) {
  return (
    <div className="flex gap-6">
      <div className="flex-shrink-0 w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center font-bold text-indigo-600 dark:text-indigo-400">
        {number}
      </div>
      <div>
        <h4 className="text-xl font-bold mb-2">{title}</h4>
        <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
          {desc}
        </p>
      </div>
    </div>
  )
}