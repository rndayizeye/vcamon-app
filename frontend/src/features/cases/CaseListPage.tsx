import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../../auth/use-auth";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useCases } from "./hooks";
import { CaseTable } from "./components/CaseTable";

export function CaseListPage() {
  const [search, setSearch] = useState("");
  const { permissions } = useAuth();
  const casesQuery = useCases(search);

  return (
    <section className="stack-lg">
      <header className="stack-sm">
        <div className="page-header-row">
          <div>
            <p className="eyebrow">Cases</p>
            <h1>Case list</h1>
          </div>

          {permissions.can_write ? (
            <Link className="button button-primary" to="/cases/new">
              Create case
            </Link>
          ) : null}
        </div>
        <p className="muted">
          Search all cases and open a record to review.
        </p>
      </header>

      <section className="panel stack-md">
        <label className="field">
          <span>Search</span>
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by patient name, diagnosis, or case manager"
          />
        </label>
      </section>

      {casesQuery.isLoading ? <LoadingState message="Loading cases…" /> : null}

      {casesQuery.isError ? (
        <ErrorState
          title="Unable to load cases"
          message={casesQuery.error.message}
          onRetry={() => void casesQuery.refetch()}
        />
      ) : null}

      {casesQuery.isSuccess && casesQuery.data.length === 0 ? (
        <EmptyState
          title="No cases found"
          description="Try a different search term or clear the current filter."
        />
      ) : null}

      {casesQuery.isSuccess && casesQuery.data.length > 0 ? (
        <div className="stack-sm">
          <p className="muted small-text">
            {casesQuery.data.length} case
            {casesQuery.data.length === 1 ? "" : "s"}
          </p>
          <CaseTable cases={casesQuery.data} />
        </div>
      ) : null}
    </section>
  );
}
