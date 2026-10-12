import type { Level } from "../api/types";

export const RISK: readonly { level: Level; label: string; color: string }[] = [
  { level: 0, label: "Low", color: "#2f9e6e" },
  { level: 1, label: "Moderate", color: "#e0b000" },
  { level: 2, label: "High", color: "#f08a24" },
  { level: 3, label: "Severe", color: "#d7263d" },
  { level: 4, label: "No Travel", color: "#5b1a6b" },
];

export const riskColor = (level: Level) => RISK[level].color;

export const ROUTE_COLORS = ["#1f6feb", "#0ca5b0", "#4b5563"] as const;
