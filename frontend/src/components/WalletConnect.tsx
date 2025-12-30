'use client';

import { useState, useEffect } from 'react';
import { useAccount, useConnect, useDisconnect, useBalance } from 'wagmi';
import { injected } from 'wagmi/connectors';

export function WalletConnect() {
    const { address, isConnected } = useAccount();
    const { connect } = useConnect();
    const { disconnect } = useDisconnect();
    const { data: balance } = useBalance({ address });

    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) return null;

    if (isConnected) {
        return (
            <div className="flex items-center gap-4">
                <div className="text-right">
                    <div className="text-sm font-medium text-gray-900 bg-gray-100 px-3 py-1 rounded-full">
                        {address?.slice(0, 6)}...{address?.slice(-4)}
                    </div>
                    {balance && (
                        <div className="text-xs text-gray-500 mt-1">
                            {Number(balance.formatted).toFixed(4)} {balance.symbol}
                        </div>
                    )}
                </div>
                <button
                    onClick={() => disconnect()}
                    className="px-4 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                >
                    Disconnect
                </button>
            </div>
        );
    }

    return (
        <button
            onClick={() => connect({ connector: injected() })}
            className="px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
            Connect Wallet
        </button>
    );
}
