import { createContext } from 'react'

import type { AuthBootstrapState } from '../features/auth/hooks'

export const AuthContext = createContext<AuthBootstrapState | null>(null)
