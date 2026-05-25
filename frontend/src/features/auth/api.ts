import { apiFetch } from '../../lib/api-client'
import type { AuthMeResponse, AuthPermissions, AuthStatusResponse } from '../../lib/auth-types'

export function getAuthStatus() {
  return apiFetch<AuthStatusResponse>('/api/auth/status')
}

export function getAuthMe() {
  return apiFetch<AuthMeResponse>('/api/auth/me')
}

export function getPermissions() {
  return apiFetch<AuthPermissions>('/api/auth/permissions')
}
