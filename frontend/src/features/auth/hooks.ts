import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError } from "../../lib/api-client";
import type {
  AuthMeResponse,
  AuthPermissions,
  AuthStatusResponse,
} from "../../lib/auth-types";
import { supabase } from "../../lib/supabase";
import { getAuthMe, getAuthStatus } from "./api";

const EMPTY_PERMISSIONS: AuthPermissions = {
  can_read: false,
  can_write: false,
  can_run_analysis: false,
  can_delete_records: false,
  can_clear_map: false,
  can_delete_cases: false,
  can_manage_users: false,
};

const OPEN_ACCESS_PERMISSIONS: AuthPermissions = {
  can_read: true,
  can_write: true,
  can_run_analysis: true,
  can_delete_records: true,
  can_clear_map: true,
  can_delete_cases: true,
  can_manage_users: true,
};

export type AuthBootstrapState = {
  loading: boolean;
  sessionChecked: boolean;
  status: AuthStatusResponse | null;
  backendAuthEnabled: boolean;
  authenticated: boolean;
  user: AuthMeResponse["user"];
  permissions: AuthPermissions;
  error: string | null;
  refresh: () => Promise<void>;
};

export function useAuthBootstrap(): AuthBootstrapState {
  const [loading, setLoading] = useState(true);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [status, setStatus] = useState<AuthStatusResponse | null>(null);
  const [backendAuthEnabled, setBackendAuthEnabled] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthMeResponse["user"]>(null);
  const [permissions, setPermissions] =
    useState<AuthPermissions>(EMPTY_PERMISSIONS);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const nextStatus = await getAuthStatus();
      setStatus(nextStatus);
      setBackendAuthEnabled(nextStatus.enabled);

      try {
        const me = await getAuthMe();
        setAuthenticated(me.authenticated);
        setUser(me.user);
        setPermissions(
          nextStatus.enabled ? me.permissions : OPEN_ACCESS_PERMISSIONS,
        );
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          setAuthenticated(false);
          setUser(null);
          setPermissions(
            nextStatus.enabled ? EMPTY_PERMISSIONS : OPEN_ACCESS_PERMISSIONS,
          );
        } else {
          throw err;
        }
      }
    } catch (err) {
      setAuthenticated(false);
      setUser(null);
      setPermissions(EMPTY_PERMISSIONS);
      setError(
        err instanceof Error
          ? err.message
          : "Unable to bootstrap authentication",
      );
    } finally {
      setLoading(false);
      setSessionChecked(true);
    }
  }, []);

  useEffect(() => {
    const refreshTimer = window.setTimeout(() => {
      void refresh();
    }, 0);

    if (!supabase) {
      return () => {
        window.clearTimeout(refreshTimer);
      };
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(() => {
      void refresh();
    });

    return () => {
      window.clearTimeout(refreshTimer);
      subscription.unsubscribe();
    };
  }, [refresh]);

  return useMemo(
    () => ({
      loading,
      sessionChecked,
      status,
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
      status,
      backendAuthEnabled,
      authenticated,
      user,
      permissions,
      error,
      refresh,
    ],
  );
}
