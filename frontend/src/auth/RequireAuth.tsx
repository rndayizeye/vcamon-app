import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { ErrorState } from "../components/feedback/ErrorState";
import { LoadingState } from "../components/feedback/LoadingState";
import { useAuth } from "./use-auth";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { loading, backendAuthEnabled, authenticated, error } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingState message="Loading session…" />;
  }

  if (error && backendAuthEnabled && !authenticated) {
    return (
      <ErrorState title="Unable to load authentication state" message={error} />
    );
  }

  if (backendAuthEnabled && !authenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }

  return <>{children}</>;
}
