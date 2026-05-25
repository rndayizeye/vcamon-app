# React Auth Bootstrap Example

This is a copy-pastable example for the planned React frontend.
It shows how to:

- initialize `supabase-js`
- forward the Supabase access token to FastAPI as a bearer token
- bootstrap the frontend session from `/api/auth/me`
- read `/api/auth/permissions`
- gate destructive UI actions based on backend permissions

This example assumes:

- React + Vite
- Supabase Auth on the client
- FastAPI auth middleware enabled on the backend when needed

See also:
- `documents/fastapi-auth-contract.md`

---

## Frontend env vars

For a Vite app, define these in `.env.local`:

```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_API_BASE_URL=http://localhost:8000
```

If the FastAPI app is hosted elsewhere, point `VITE_API_BASE_URL` at that deployed API.

---

## 1. Supabase client

Create `src/lib/supabase.ts`:

```ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
)
```

---

## 2. Backend auth response types

Create `src/lib/auth-types.ts`:

```ts
export type AuthPermissions = {
  can_read: boolean
  can_write: boolean
  can_run_analysis: boolean
  can_delete_records: boolean
  can_clear_map: boolean
  can_delete_cases: boolean
  can_manage_users: boolean
}

export type AuthenticatedUser = {
  id: string
  email: string | null
  role: string | null
  app_metadata: Record<string, unknown>
  user_metadata: Record<string, unknown>
}

export type AuthMeResponse = {
  enabled: boolean
  authenticated: boolean
  provider: string
  user: AuthenticatedUser | null
  permissions: AuthPermissions
}

export type AuthStatusResponse = {
  enabled: boolean
  provider: string
  environment: string
  ready: boolean
  missing_configuration: string[]
  public_paths: string[]
}
```

---

## 3. API client that forwards the Supabase token

Create `src/lib/api-client.ts`:

```ts
import { supabase } from './supabase'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
  } = await supabase.auth.getSession()

  return session?.access_token ?? null
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = await getAccessToken()

  const headers = new Headers(init.headers ?? {})
  headers.set('Accept', 'application/json')

  const hasBody = init.body !== undefined && init.body !== null
  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    let detail = response.statusText

    try {
      const payload = await response.json()
      detail = payload.detail ?? JSON.stringify(payload)
    } catch {
      // keep statusText fallback
    }

    throw new Error(`API ${response.status}: ${detail}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
```

---

## 4. Auth bootstrap hook

Create `src/hooks/use-auth-bootstrap.ts`:

```ts
import { useEffect, useMemo, useState } from 'react'
import { supabase } from '../lib/supabase'
import { apiFetch } from '../lib/api-client'
import type { AuthMeResponse, AuthPermissions } from '../lib/auth-types'

const EMPTY_PERMISSIONS: AuthPermissions = {
  can_read: false,
  can_write: false,
  can_run_analysis: false,
  can_delete_records: false,
  can_clear_map: false,
  can_delete_cases: false,
  can_manage_users: false,
}

type AuthBootstrapState = {
  loading: boolean
  sessionChecked: boolean
  backendAuthEnabled: boolean
  authenticated: boolean
  user: AuthMeResponse['user']
  permissions: AuthPermissions
  error: string | null
  refresh: () => Promise<void>
}

export function useAuthBootstrap(): AuthBootstrapState {
  const [loading, setLoading] = useState(true)
  const [sessionChecked, setSessionChecked] = useState(false)
  const [backendAuthEnabled, setBackendAuthEnabled] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)
  const [user, setUser] = useState<AuthMeResponse['user']>(null)
  const [permissions, setPermissions] = useState<AuthPermissions>(EMPTY_PERMISSIONS)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    setError(null)

    try {
      const me = await apiFetch<AuthMeResponse>('/api/auth/me')
      setBackendAuthEnabled(me.enabled)
      setAuthenticated(me.authenticated)
      setUser(me.user)
      setPermissions(me.permissions)
    } catch (err) {
      setAuthenticated(false)
      setUser(null)
      setPermissions(EMPTY_PERMISSIONS)
      setError(err instanceof Error ? err.message : 'Unknown auth bootstrap error')
    } finally {
      setLoading(false)
      setSessionChecked(true)
    }
  }

  useEffect(() => {
    void refresh()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      void refresh()
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  return useMemo(
    () => ({
      loading,
      sessionChecked,
      backendAuthEnabled,
      authenticated,
      user,
      permissions,
      error,
      refresh,
    }),
    [
      loading,
      sessionChecked,
      backendAuthEnabled,
      authenticated,
      user,
      permissions,
      error,
    ],
  )
}
```

---

## 5. Auth context provider

Create `src/auth/auth-context.tsx`:

```tsx
import { createContext, useContext } from 'react'
import { useAuthBootstrap } from '../hooks/use-auth-bootstrap'

type AuthContextValue = ReturnType<typeof useAuthBootstrap>

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuthBootstrap()
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return value
}
```

---

## 6. Permission gate component

Create `src/auth/RequirePermission.tsx`:

```tsx
import { useAuth } from './auth-context'
import type { AuthPermissions } from '../lib/auth-types'

type PermissionKey = keyof AuthPermissions

export function RequirePermission({
  permission,
  fallback = null,
  children,
}: {
  permission: PermissionKey
  fallback?: React.ReactNode
  children: React.ReactNode
}) {
  const { permissions } = useAuth()

  if (!permissions[permission]) {
    return <>{fallback}</>
  }

  return <>{children}</>
}
```

---

## 7. App bootstrap example

Create `src/App.tsx`:

```tsx
import { AuthProvider, useAuth } from './auth/auth-context'
import { RequirePermission } from './auth/RequirePermission'
import { supabase } from './lib/supabase'

function AppShell() {
  const { loading, authenticated, user, permissions, error } = useAuth()

  if (loading) {
    return <div>Loading session…</div>
  }

  return (
    <main style={{ padding: 24, fontFamily: 'sans-serif' }}>
      <h1>VCA Monitor v2</h1>

      {error ? <p style={{ color: 'crimson' }}>{error}</p> : null}

      <p>Authenticated: {authenticated ? 'yes' : 'no'}</p>
      <p>User: {user?.email ?? 'anonymous'}</p>
      <p>Role: {user?.role ?? 'none'}</p>

      <pre>{JSON.stringify(permissions, null, 2)}</pre>

      <button
        onClick={async () => {
          await supabase.auth.signInWithOtp({
            email: 'caseworker@example.com',
            options: {
              emailRedirectTo: window.location.origin,
            },
          })
        }}
      >
        Send sign-in link
      </button>

      <button
        onClick={async () => {
          await supabase.auth.signOut({ scope: 'local' })
        }}
      >
        Sign out
      </button>

      <hr />

      <section>
        <h2>Case editing</h2>
        {permissions.can_write ? (
          <button>Create case</button>
        ) : (
          <p>You do not have write access.</p>
        )}
        <p>
          When you implement the React create/edit form, use a
          <code>diagnosis_code</code> field in form state and request payloads.
          Treat <code>lot</code> as a legacy compatibility field rather than a
          new form input name.
        </p>
      </section>

      <section>
        <h2>Destructive actions</h2>
        <RequirePermission
          permission="can_delete_cases"
          fallback={<p>Delete case is supervisor-only.</p>}
        >
          <button style={{ color: 'crimson' }}>Delete case</button>
        </RequirePermission>
      </section>
    </main>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  )
}
```

---

## 8. Example API call after bootstrap

Once the user is signed in, your normal API calls can go through `apiFetch`.

Example:

```ts
import { apiFetch } from './lib/api-client'

type CaseSummary = {
  id: number
  patient_name: string
  diagnosis_code: string | null
  lot: string | null
  case_manager: string | null
  initial_contact_date: string | null
  updated_at: string | null
}

export async function listCases(search?: string) {
  const query = search ? `?search=${encodeURIComponent(search)}` : ''
  return apiFetch<CaseSummary[]>(`/api/cases/${query}`)
}
```

For writes:

```ts
type CaseCreateInput = {
  patient_name: string
  diagnosis_code?: string | null
  case_manager?: string | null
}

type CaseUpdateInput = Partial<CaseCreateInput>

export async function createCase(input: CaseCreateInput) {
  return apiFetch('/api/cases/', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function updateCase(caseId: number, input: CaseUpdateInput) {
  return apiFetch(`/api/cases/${caseId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}
```

The backend now accepts `diagnosis_code` as a clearer alias for the legacy `lot`
field and also returns `diagnosis_code` in case responses. Existing clients that
still send or read `lot` remain compatible during the transition, but new React
case create/edit forms should submit `diagnosis_code` and avoid introducing a
new `lot` form field.

---

## 9. UI guidance

Use backend permission flags for UI gating instead of hardcoding role names.

Good:
- `if (permissions.can_delete_cases) { ... }`

Avoid:
- `if (user.role === 'supervisor') { ... }`

That keeps the frontend stable if backend RBAC rules evolve.

---

## 10. Error handling notes

Expected failure modes:

- `401 Missing or invalid bearer token`
  - no valid Supabase session/token was attached
- `401 Invalid or expired access token`
  - Supabase token is stale or invalid
- `403 Insufficient role`
  - user is authenticated but lacks permission for a destructive action
- `503 Supabase auth is enabled but required configuration is missing`
  - backend env is incomplete
- `502 Unable to reach Supabase auth service`
  - backend cannot validate tokens against Supabase

The frontend should surface these distinctly where possible.

---

## 11. Recommended next frontend step

Once the actual React app exists, the next good implementation step is:

1. add a tiny `auth/` module from this example
2. wire `AuthProvider` into the app root
3. build the dashboard case list against `GET /api/cases/`
4. gate destructive buttons with `RequirePermission`

That gives you a clean starting slice for the real migration.
