'use client';

import { WagmiProvider, createConfig, http } from 'wagmi';
import { hardhat, mainnet, sepolia } from 'wagmi/chains';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode } from 'react';

const config = createConfig({
    chains: [hardhat, sepolia, mainnet],
    transports: {
        [hardhat.id]: http(),
        [sepolia.id]: http(),
        [mainnet.id]: http(),
    },
});

const queryClient = new QueryClient();

export function Web3Provider({ children }: { children: ReactNode }) {
    return (
        <WagmiProvider config={config}>
            <QueryClientProvider client={queryClient}>
                {children}
            </QueryClientProvider>
        </WagmiProvider>
    );
}
