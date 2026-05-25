import type { ReactNode } from "react";

import { useAuthBootstrap } from "../features/auth/hooks";
import { AuthContext } from "./auth-context-store";

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuthBootstrap();
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}
