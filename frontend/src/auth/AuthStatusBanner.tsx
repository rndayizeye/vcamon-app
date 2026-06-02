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
        Authentication is enabled but not fully configured. Missing:{" "}
        {status.missing_configuration.join(", ")}.
      </div>
    );
  }

  if (!status.enabled) {
    return (
      <div className="banner banner-info">
        Authentication is not required in this environment.
      </div>
    );
  }

  return (
    <div className="banner banner-success">
      Authenticated.
    </div>
  );
}
