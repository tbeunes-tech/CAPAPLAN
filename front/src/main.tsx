import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./AuthContext";
import { WindowProvider } from "./WindowContext";
import PortfolioPage from "./pages/PortfolioPage";
import LoadGridPage from "./pages/LoadGridPage";
import TeamLoadPage from "./pages/TeamLoadPage";
import CapacityPage from "./pages/CapacityPage";
import OccupancyPage from "./pages/OccupancyPage";
import OverloadsPage from "./pages/OverloadsPage";
import RoadmapPage from "./pages/RoadmapPage";
import PrioritizationPage from "./pages/PrioritizationPage";
import TeamsPage from "./pages/TeamsPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: true, staleTime: 5_000 } },
});

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <Navigate to="/portfolio" replace /> },
      { path: "portfolio", element: <PortfolioPage /> },
      { path: "portfolio/:projectId/loads", element: <LoadGridPage /> },
      { path: "portfolio/:projectId/history", element: <HistoryPage /> },
      { path: "team-load", element: <TeamLoadPage /> },
      { path: "capacity", element: <CapacityPage /> },
      { path: "occupancy", element: <OccupancyPage /> },
      { path: "overloads", element: <OverloadsPage /> },
      { path: "roadmap", element: <RoadmapPage /> },
      { path: "prioritization", element: <PrioritizationPage /> },
      { path: "teams", element: <TeamsPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <WindowProvider>
          <RouterProvider router={router} />
        </WindowProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
