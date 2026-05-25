import { NavLink, Outlet, useParams } from "react-router-dom";

import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { CaseHeader } from "../../features/cases/components/CaseHeader";
import { useCase } from "../../features/cases/hooks";

export function CaseLayout() {
  const { caseId } = useParams();
  const parsedCaseId = Number(caseId);
  const safeCaseId =
    Number.isInteger(parsedCaseId) && parsedCaseId > 0 ? parsedCaseId : 0;
  const caseQuery = useCase(safeCaseId);

  if (safeCaseId === 0) {
    return (
      <ErrorState title="Invalid case" message="The case id is not valid." />
    );
  }

  if (caseQuery.isLoading) {
    return <LoadingState message="Loading case…" />;
  }

  if (caseQuery.isError) {
    return (
      <ErrorState
        title="Unable to load case"
        message={caseQuery.error.message}
        onRetry={() => void caseQuery.refetch()}
      />
    );
  }

  if (!caseQuery.data) {
    return (
      <ErrorState title="Case not found" message="No case was returned." />
    );
  }

  return (
    <section className="stack-lg">
      <CaseHeader caseData={caseQuery.data} />

      <nav className="tab-nav" aria-label="Case sections">
        <NavLink
          to="overview"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          Overview
        </NavLink>
        <NavLink
          to="partners"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          Partners
        </NavLink>
        <NavLink
          to="analytics"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          Analytics
        </NavLink>
        <NavLink
          to="network"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          Network
        </NavLink>
        <NavLink
          to="timeline"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          Timeline
        </NavLink>
        <NavLink
          to="map"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          MAP
        </NavLink>
        <NavLink
          to="ghosting"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          Ghosting
        </NavLink>
        <NavLink
          to="vca-chart"
          className={({ isActive }) =>
            isActive ? "tab-link tab-link-active" : "tab-link"
          }
        >
          VCA Chart
        </NavLink>
      </nav>

      <Outlet />
    </section>
  );
}
