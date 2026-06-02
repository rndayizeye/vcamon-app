import { NavLink, Outlet, useParams } from "react-router-dom";

import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { CaseHeader } from "../../features/cases/components/CaseHeader";
import { useCase } from "../../features/cases/hooks";

const TAB_LINKS: { to: string; label: string; title?: string }[] = [
  { to: "overview",  label: "Overview" },
  { to: "partners",  label: "Partners" },
  { to: "timeline",  label: "Timeline" },
  { to: "map",       label: "MAP",       title: "Major Analytical Points — 46-item systematic checklist" },
  { to: "ghosting",  label: "Ghosting",  title: "Ghosting Analysis — determine transmission likelihood between two patients" },
  { to: "vca-chart", label: "VCA Chart", title: "VCA Timeline — visual case analysis chart" },
  { to: "network",   label: "Network",   title: "Transmission Network — map of all contacts and links" },
  { to: "analytics", label: "Analytics", title: "Network Analytics — cluster and centrality summaries" },
];

const tabClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? "tab-link tab-link-active" : "tab-link";

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
        {TAB_LINKS.map(({ to, label, title }) => (
          <NavLink key={to} to={to} className={tabClass} title={title}>
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </section>
  );
}
