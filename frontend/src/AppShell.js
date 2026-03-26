import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

import { DashboardThemeContext, darkTheme } from "./theme";
import ErrorBoundary from "./components/ErrorBoundary";
import AppSidebar from "./components/AppSidebar";

import EnhancedQuantumPortfolioDashboard from "./CustomizableQuantumDashboard";
import BacktestPage from "./pages/BacktestPage";
import RiskPage from "./pages/RiskPage";
import ScenariosPage from "./pages/ScenariosPage";
import SettingsPage from "./pages/SettingsPage";

const SIDEBAR_W = 64;

export default function AppShell() {
  return (
    <DashboardThemeContext.Provider value={darkTheme}>
      <BrowserRouter>
        <div style={{ display: "flex", minHeight: "100vh", background: darkTheme.bg }}>
          <AppSidebar />

          {/* Main content pushed right of the sidebar */}
          <div style={{ marginLeft: SIDEBAR_W, flex: 1, minWidth: 0, overflowY: "auto" }}>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<EnhancedQuantumPortfolioDashboard />} />
                <Route path="/backtest" element={<BacktestPage />} />
                <Route path="/risk" element={<RiskPage />} />
                <Route path="/scenarios" element={<ScenariosPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </ErrorBoundary>
          </div>
        </div>

        <ToastContainer
          position="bottom-right"
          autoClose={4000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnFocusLoss={false}
          draggable
          theme="dark"
        />
      </BrowserRouter>
    </DashboardThemeContext.Provider>
  );
}
