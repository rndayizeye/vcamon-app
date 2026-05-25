import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'

import { AuthProvider } from '../auth/auth-context'
import { queryClient } from './query-client'

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}
