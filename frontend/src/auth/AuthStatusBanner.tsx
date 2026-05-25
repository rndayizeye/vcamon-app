import { useAuth } from "./use-auth";

export function AuthStatusBanner() {
  const { loading, error, status } = useAuth();

  if (loading) {
    return null;
  }

  if (error && !status) {
    return <div className="banner banner-danger">{error}</div>;
  }

  if (!status) {
    return null;
  }

  if (status.enabled && !status.ready) {
    return (
      <div className="banner banner-danger">
        Backend auth is enabled but not ready. Missing:{" "}
        {status.missing_configuration.join(", ")}.
      </div>
    );
  }

  if (!status.enabled) {
    return (
      <div className="banner banner-info">
        Backend auth is disabled in this environment. The app is running in open
        access mode.
      </div>
    );
  }

  return (
    <div className="banner banner-success">
      Backend auth is enabled and ready for authenticated API calls.
    </div>
  );
}
