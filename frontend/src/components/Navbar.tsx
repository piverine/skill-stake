'use client'

import Link from 'next/link'
import { WalletConnect } from './WalletConnect'
import { UserButton, useUser } from '@clerk/nextjs'

export default function Navbar() {
    const { isLoaded, isSignedIn } = useUser()

    return (
        <nav className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-16">
                    <div className="flex">
                        <Link href="/" className="flex-shrink-0 flex items-center">
                            <span className="text-xl font-bold text-blue-600">SkillStake</span>
                        </Link>
                        <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                            <Link
                                href="/dashboard"
                                className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                            >
                                Dashboard
                            </Link>
                        </div>
                    </div>
                    <div className="flex items-center space-x-4">
                        <WalletConnect />
                        {isLoaded && isSignedIn && <UserButton afterSignOutUrl="/" />}
                    </div>
                </div>
            </div>
        </nav>
    )
}
