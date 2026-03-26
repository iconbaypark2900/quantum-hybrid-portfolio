import React, { useState, useContext } from "react";
import { DashboardThemeContext } from "../theme";
import { FaCheckCircle, FaExclamationCircle, FaAtom } from "react-icons/fa";
import api from "../services/api";

async function testIbmQuantumConnection(token) {
  const res = await api.post("/api/quantum/ibm/test", { token });
  return res.data;
}

export default function SettingsPage() {
  const colors = useContext(DashboardThemeContext);
  const [ibmToken, setIbmToken] = useState(localStorage.getItem("ibm_quantum_token") || "");
  const [ibmStatus, setIbmStatus] = useState(null);
  const [ibmLoading, setIbmLoading] = useState(false);
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem("api_base_url") || window.location.origin
  );
  const [saved, setSaved] = useState(false);

  const testIbm = async () => {
    setIbmLoading(true);
    setIbmStatus(null);
    try {
      const res = await testIbmQuantumConnection(ibmToken);
      setIbmStatus({ ok: true, msg: res?.message || "Connected" });
    } catch (e) {
      setIbmStatus({ ok: false, msg: e?.message || "Connection failed" });
    } finally {
      setIbmLoading(false);
    }
  };

  const save = () => {
    if (ibmToken) localStorage.setItem("ibm_quantum_token", ibmToken);
    if (apiUrl) localStorage.setItem("api_base_url", apiUrl);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const card = {
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: 10,
    padding: "22px 26px",
    marginBottom: 20,
  };

  const label = {
    fontSize: 11,
    color: colors.textMuted,
    marginBottom: 6,
    display: "block",
    fontWeight: 600,
    letterSpacing: "0.05em",
  };

  const input = {
    width: "100%",
    background: colors.surfaceLight,
    border: `1px solid ${colors.border}`,
    borderRadius: 7,
    color: colors.text,
    padding: "8px 12px",
    fontSize: 13,
    fontFamily: "monospace",
    boxSizing: "border-box",
  };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 680 }}>
      <h1 style={{ color: colors.text, fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Settings
      </h1>
      <p style={{ color: colors.textMuted, fontSize: 13, marginBottom: 28 }}>
        Configure API connections and quantum hardware credentials.
      </p>

      {/* IBM Quantum */}
      <div style={card}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 18 }}>
          <FaAtom style={{ color: "#3B82F6", fontSize: 18 }} />
          <span style={{ color: colors.text, fontWeight: 700, fontSize: 15 }}>IBM Quantum</span>
        </div>

        <label style={label}>API Token</label>
        <input
          type="password"
          value={ibmToken}
          onChange={(e) => setIbmToken(e.target.value)}
          placeholder="Paste your IBM Quantum token…"
          style={input}
        />

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 14 }}>
          <button
            onClick={testIbm}
            disabled={!ibmToken || ibmLoading}
            style={{
              padding: "7px 18px",
              background: !ibmToken || ibmLoading ? colors.border : "#3B82F6",
              color: "#fff",
              border: "none",
              borderRadius: 7,
              cursor: !ibmToken || ibmLoading ? "not-allowed" : "pointer",
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            {ibmLoading ? "Testing…" : "Test Connection"}
          </button>

          {ibmStatus && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                color: ibmStatus.ok ? colors.green : colors.red,
              }}
            >
              {ibmStatus.ok ? <FaCheckCircle /> : <FaExclamationCircle />}
              {ibmStatus.msg}
            </div>
          )}
        </div>
      </div>

      {/* API URL */}
      <div style={card}>
        <div style={{ color: colors.text, fontWeight: 700, fontSize: 15, marginBottom: 16 }}>
          Backend API
        </div>
        <label style={label}>API Base URL</label>
        <input
          type="text"
          value={apiUrl}
          onChange={(e) => setApiUrl(e.target.value)}
          placeholder="http://localhost:5000"
          style={input}
        />
        <div style={{ fontSize: 11, color: colors.textDim, marginTop: 6 }}>
          Defaults to current origin in HF Space deployments.
        </div>
      </div>

      {/* Save */}
      <button
        onClick={save}
        style={{
          padding: "9px 28px",
          background: saved ? colors.green : "#3B82F6",
          color: "#fff",
          border: "none",
          borderRadius: 8,
          cursor: "pointer",
          fontWeight: 700,
          fontSize: 14,
          transition: "background 0.2s",
        }}
      >
        {saved ? "Saved!" : "Save Settings"}
      </button>
    </div>
  );
}
