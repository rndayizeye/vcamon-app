import { NavLink, Outlet, useParams } from "react-router-dom";

import { ErrorState } from "../feedback/ErrorState";
import { LoadingState } from "../feedback/LoadingState";
import { CaseHeader } from "../../features/cases/components/CaseHeader";
import { useCase } from "../../features/cases/hooks";

const TAB_LINKS = [
  { to: "overview",   label: "Overview" },
  { to: "partners",   label: "Partners" },
  { to: "analytics",  label: "Analytics" },
  { to: "network",    label: "Network" },
  { to: "timeline",   label: "Timeline" },
  { to: "map",        label: "MAP" },
  { to: "ghosting",   label: "Ghosting" },
  { to: "vca-chart",  label: "VCA Chart" },
] as const;

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
        {TAB_LINKS.map(({ to, label }) => (
          <NavLink key={to} to={to} className={tabClass}>
            {label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </section>
  );
}
