import React from "react";
import EnhancedQuantumPortfolioDashboard from "./EnhancedQuantumDashboard";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

export default function QuantumPortfolioDashboard() {
  return (
    <ErrorBoundary>
      <EnhancedQuantumPortfolioDashboard />
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
    </ErrorBoundary>
  );
}
