import { Link } from "react-router-dom";

import { supabase } from "../../lib/supabase";
import { useAuth } from "../../auth/use-auth";

export function TopBar() {
  const { authenticated, backendAuthEnabled, user } = useAuth();

  async function handleSignOut() {
    if (!supabase) {
      return;
    }
    await supabase.auth.signOut({ scope: "local" });
  }

  return (
    <header className="topbar">
      <div className="stack-xs">
        <Link className="brand-link" to="/cases">
          VCA Monitor
        </Link>
        <span className="muted small-text">
          Syphilis case and contact management
        </span>
      </div>

      <div className="topbar-actions">
        <span className="muted small-text">
          {backendAuthEnabled
            ? authenticated
              ? user?.email || "Authenticated user"
              : "Signed out"
            : "Open access mode"}
        </span>

        {backendAuthEnabled && authenticated ? (
          <button className="button" type="button" onClick={handleSignOut}>
            Sign out
          </button>
        ) : null}
      </div>
    </header>
  );
}
