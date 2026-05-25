import type { ReactNode } from "react";

import type { AuthPermissions } from "../lib/auth-types";
import { useAuth } from "./use-auth";

type PermissionKey = keyof AuthPermissions;

export function RequirePermission({
  permission,
  fallback = null,
  children,
}: {
  permission: PermissionKey;
  fallback?: ReactNode;
  children: ReactNode;
}) {
  const { permissions } = useAuth();

  if (!permissions[permission]) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
