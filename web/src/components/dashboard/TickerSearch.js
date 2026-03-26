"use client";

import React, { useState, useRef, useCallback, useEffect, useMemo, useContext } from "react";
import { DashboardThemeContext } from "@/lib/theme";
import { searchTickers } from "@/data/tickerCatalog";

const TYPE_BADGE = { etf: "ETF", stock: "STK", index: "IDX", custom: "?" };

/**
 * Reusable ticker search with autocomplete dropdown and chip display.
 *
 * Props:
 *   value       - string[] of selected ticker symbols
 *   onChange     - (tickers: string[]) => void
 *   placeholder  - input placeholder (default "Search tickers...")
 *   compact      - boolean, if true renders a more compact layout (for table cells)
 */
function TickerSearch({ value = [], onChange, placeholder = "Search tickers...", compact = false }) {
  const colors = useContext(DashboardThemeContext);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);

  const trimmed = query.trim();
  const results = useMemo(() => {
    if (!trimmed) return [];
    const hits = searchTickers(query, 12);
    const selected = new Set(value.map((t) => t.toUpperCase()));
    return hits.filter((h) => !selected.has(h.symbol));
  }, [query, value, trimmed]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const addTicker = useCallback(
    (symbol) => {
      const sym = symbol.trim().toUpperCase();
      if (!sym) return;
      if (!value.map((t) => t.toUpperCase()).includes(sym)) {
        onChange([...value, sym]);
      }
      setQuery("");
      setOpen(false);
      inputRef.current?.focus();
    },
    [value, onChange]
  );

  const removeTicker = useCallback(
    (symbol) => {
      onChange(value.filter((t) => t.toUpperCase() !== symbol.toUpperCase()));
    },
    [value, onChange]
  );

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightIdx((prev) => Math.min(prev + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightIdx((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (highlightIdx >= 0 && results[highlightIdx]) {
          addTicker(results[highlightIdx].symbol);
        } else if (query.trim()) {
          addTicker(query);
        }
      } else if (e.key === "Backspace" && !query && value.length > 0) {
        removeTicker(value[value.length - 1]);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    },
    [highlightIdx, results, query, value, addTicker, removeTicker]
  );

  const chipSize = compact ? 9 : 11;
  const inputFontSize = compact ? 11 : 12;

  return (
    <div ref={wrapperRef} style={{ position: "relative", width: "100%" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: compact ? 3 : 4,
          padding: compact ? "4px 6px" : "6px 10px",
          background: colors.surfaceLight,
          border: `1px solid ${colors.border}`,
          borderRadius: compact ? 4 : 6,
          alignItems: "center",
          minHeight: compact ? 28 : 34,
          cursor: "text",
        }}
        onClick={() => inputRef.current?.focus()}
      >
        {value.map((sym) => (
          <span
            key={sym}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 3,
              padding: compact ? "1px 5px" : "2px 8px",
              background: `${colors.accent}18`,
              border: `1px solid ${colors.accent}40`,
              borderRadius: 4,
              fontSize: chipSize,
              color: colors.accent,
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 600,
              whiteSpace: "nowrap",
            }}
          >
            {sym}
            <span
              onClick={(e) => {
                e.stopPropagation();
                removeTicker(sym);
              }}
              style={{
                cursor: "pointer",
                marginLeft: 2,
                color: colors.textDim,
                fontSize: compact ? 10 : 12,
                lineHeight: 1,
              }}
              title={`Remove ${sym}`}
            >
              {"\u00d7"}
            </span>
          </span>
        ))}
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => {
            const v = e.target.value;
            setQuery(v);
            setHighlightIdx(-1);
            if (!v.trim()) {
              setOpen(false);
            } else {
              setOpen(true);
            }
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (query.trim()) setOpen(true); }}
          placeholder={value.length === 0 ? placeholder : ""}
          style={{
            flex: 1,
            minWidth: 70,
            border: "none",
            outline: "none",
            background: "transparent",
            color: colors.text,
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: inputFontSize,
            padding: 0,
          }}
        />
      </div>

      {open && results.length > 0 && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            right: 0,
            zIndex: 1000,
            maxHeight: 260,
            overflowY: "auto",
            background: colors.surface,
            border: `1px solid ${colors.border}`,
            borderTop: "none",
            borderRadius: "0 0 6px 6px",
            boxShadow: `0 8px 24px ${colors.bg}80`,
          }}
        >
          {results.map((item, idx) => (
            <div
              key={item.symbol}
              onMouseDown={(e) => {
                e.preventDefault();
                addTicker(item.symbol);
              }}
              onMouseEnter={() => setHighlightIdx(idx)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "7px 12px",
                cursor: "pointer",
                background: idx === highlightIdx ? colors.surfaceLight : "transparent",
                transition: "background 0.1s",
              }}
            >
              <span
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 12,
                  fontWeight: 700,
                  color: colors.accent,
                  minWidth: 52,
                }}
              >
                {item.symbol}
              </span>
              <span style={{ flex: 1, fontSize: 11, color: colors.textMuted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {item.name}
              </span>
              <span
                style={{
                  fontSize: 8,
                  padding: "1px 5px",
                  borderRadius: 3,
                  fontFamily: "'JetBrains Mono', monospace",
                  color: item.type === "etf" ? colors.green : item.type === "stock" ? colors.purple : colors.textDim,
                  background: item.type === "etf" ? `${colors.green}15` : item.type === "stock" ? `${colors.purple}15` : `${colors.textDim}15`,
                  border: `1px solid ${item.type === "etf" ? colors.green : item.type === "stock" ? colors.purple : colors.textDim}30`,
                  textTransform: "uppercase",
                }}
              >
                {TYPE_BADGE[item.type] || item.type}
              </span>
              <span style={{ fontSize: 9, color: colors.textDim, minWidth: 60, textAlign: "right" }}>{item.sector}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default React.memo(TickerSearch);
