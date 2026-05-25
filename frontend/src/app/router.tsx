import { Navigate, createBrowserRouter } from "react-router-dom";

import { LoginPage } from "../auth/LoginPage";
import { RequireAuth } from "../auth/RequireAuth";
import { CaseLayout } from "../components/layout/CaseLayout";
import { AppShell } from "../components/layout/AppShell";
import { CaseAnalyticsPage } from "../features/analytics/CaseAnalyticsPage";
import { CaseCreatePage } from "../features/cases/CaseCreatePage";
import { CaseEditPage } from "../features/cases/CaseEditPage";
import { DashboardPage } from "../pages/DashboardPage";
import { CaseOverviewPage } from "../features/cases/CaseOverviewPage";
import { CaseMapPage } from "../features/map/CaseMapPage";
import { PartnerListPage } from "../features/partners/PartnerListPage";
import { PartnerCreatePage } from "../features/partners/PartnerCreatePage";
import { PartnerEditPage } from "../features/partners/PartnerEditPage";
import { GhostingPage } from "../features/ghosting/GhostingPage";
import { VcaChartPage } from "../features/ghosting/VcaChartPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
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
        element: <DashboardPage />,
      },
      {
        path: "cases/new",
        element: <CaseCreatePage />,
      },
      {
        path: "cases/:caseId/edit",
        element: <CaseEditPage />,
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
            element: <CaseOverviewPage />,
          },
          {
            path: "partners",
            element: <PartnerListPage />,
          },
          {
            path: "partners/new",
            element: <PartnerCreatePage />,
          },
          {
            path: "partners/:partnerId/edit",
            element: <PartnerEditPage />,
          },
          {
            path: "analytics",
            element: <CaseAnalyticsPage />,
          },
          {
            path: "map",
            element: <CaseMapPage />,
          },
          {
            path: "ghosting",
            element: <GhostingPage />,
          },
          {
            path: "vca-chart",
            element: <VcaChartPage />,
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <Navigate to="/cases" replace />,
  },
]);
