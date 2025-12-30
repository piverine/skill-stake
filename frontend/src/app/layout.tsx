import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { Web3Provider } from '@/components/providers/Web3Provider'
import Navbar from '@/components/Navbar'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Skill-Stake Learning Platform',
  description: 'Blockchain-incentivized learning verification platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={inter.className}>
          <Web3Provider>
            <Navbar />
            {children}
          </Web3Provider>
        </body>
      </html>
    </ClerkProvider>
  )
}