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
