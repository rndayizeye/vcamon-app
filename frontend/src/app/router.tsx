/* eslint-disable react-refresh/only-export-components */
import { lazy, Suspense } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";

import { LoginPage } from "../auth/LoginPage";
import { RequireAuth } from "../auth/RequireAuth";
import { CaseLayout } from "../components/layout/CaseLayout";
import { AppShell } from "../components/layout/AppShell";
import { LoadingState } from "../components/feedback/LoadingState";
import { PageErrorBoundary } from "../components/feedback/PageErrorBoundary";

const CaseAnalyticsPage = lazy(() =>
  import("../features/analytics/CaseAnalyticsPage").then(m => ({ default: m.CaseAnalyticsPage }))
);
const CaseCreatePage = lazy(() =>
  import("../features/cases/CaseCreatePage").then(m => ({ default: m.CaseCreatePage }))
);
const CaseEditPage = lazy(() =>
  import("../features/cases/CaseEditPage").then(m => ({ default: m.CaseEditPage }))
);
const DashboardPage = lazy(() =>
  import("../pages/DashboardPage").then(m => ({ default: m.DashboardPage }))
);
const CaseOverviewPage = lazy(() =>
  import("../features/cases/CaseOverviewPage").then(m => ({ default: m.CaseOverviewPage }))
);
const CaseMapPage = lazy(() =>
  import("../features/map/CaseMapPage").then(m => ({ default: m.CaseMapPage }))
);
const PartnerListPage = lazy(() =>
  import("../features/partners/PartnerListPage").then(m => ({ default: m.PartnerListPage }))
);
const PartnerCreatePage = lazy(() =>
  import("../features/partners/PartnerCreatePage").then(m => ({ default: m.PartnerCreatePage }))
);
const PartnerEditPage = lazy(() =>
  import("../features/partners/PartnerEditPage").then(m => ({ default: m.PartnerEditPage }))
);
const GhostingPage = lazy(() =>
  import("../features/ghosting/GhostingPage").then(m => ({ default: m.GhostingPage }))
);
const QuickGhostPage = lazy(() =>
  import("../features/ghosting/QuickGhostPage").then(m => ({ default: m.QuickGhostPage }))
);
const VcaChartPage = lazy(() =>
  import("../features/ghosting/VcaChartPage").then(m => ({ default: m.VcaChartPage }))
);
const NetworkGraphPage = lazy(() =>
  import("../features/network/NetworkGraphPage").then(m => ({ default: m.NetworkGraphPage }))
);
const TimelinePage = lazy(() =>
  import("../features/timeline/TimelinePage").then(m => ({ default: m.TimelinePage }))
);
const TransmissionChainPage = lazy(() =>
  import("../features/transmission/TransmissionChainPage").then(m => ({
    default: m.TransmissionChainPage,
  }))
);

function RouteSuspense({ children }: { children: React.ReactNode }) {
  return (
    <PageErrorBoundary>
      <Suspense fallback={<LoadingState />}>{children}</Suspense>
    </PageErrorBoundary>
  );
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <PageErrorBoundary>
        <LoginPage />
      </PageErrorBoundary>
    ),
  },
  {
    path: "/",
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/cases" replace />,
      },
      {
        path: "cases",
        element: (
          <RouteSuspense>
            <DashboardPage />
          </RouteSuspense>
        ),
      },
      {
        path: "cases/new",
        element: (
          <RouteSuspense>
            <CaseCreatePage />
          </RouteSuspense>
        ),
      },
      {
        path: "cases/:caseId/edit",
        element: (
          <RouteSuspense>
            <CaseEditPage />
          </RouteSuspense>
        ),
      },
      {
        path: "cases/:caseId",
        element: <CaseLayout />,
        children: [
          {
            index: true,
            element: <Navigate to="analytics" replace />,
          },
          {
            path: "overview",
            element: (
              <RouteSuspense>
                <CaseOverviewPage />
              </RouteSuspense>
            ),
          },
          {
            path: "partners",
            element: (
              <RouteSuspense>
                <PartnerListPage />
              </RouteSuspense>
            ),
          },
          {
            path: "partners/new",
            element: (
              <RouteSuspense>
                <PartnerCreatePage />
              </RouteSuspense>
            ),
          },
          {
            path: "partners/:partnerId/edit",
            element: (
              <RouteSuspense>
                <PartnerEditPage />
              </RouteSuspense>
            ),
          },
          {
            path: "analytics",
            element: (
              <RouteSuspense>
                <CaseAnalyticsPage />
              </RouteSuspense>
            ),
          },
          {
            path: "map",
            element: (
              <RouteSuspense>
                <CaseMapPage />
              </RouteSuspense>
            ),
          },
          {
            path: "network",
            element: (
              <RouteSuspense>
                <NetworkGraphPage />
              </RouteSuspense>
            ),
          },
          {
            path: "timeline",
            element: (
              <RouteSuspense>
                <TimelinePage />
              </RouteSuspense>
            ),
          },
          {
            path: "ghosting",
            element: (
              <RouteSuspense>
                <GhostingPage />
              </RouteSuspense>
            ),
          },
          {
            path: "vca-chart",
            element: (
              <RouteSuspense>
                <VcaChartPage />
              </RouteSuspense>
            ),
          },
        ],
      },
      {
        path: "quick-ghost",
        element: (
          <RouteSuspense>
            <QuickGhostPage />
          </RouteSuspense>
        ),
      },
      {
        path: "transmission-chain",
        element: (
          <RouteSuspense>
            <TransmissionChainPage />
          </RouteSuspense>
        ),
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/cases" replace />,
  },
]);
