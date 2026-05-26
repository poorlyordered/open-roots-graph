export function getScoreColor(score: number): string {
  if (score >= 0.8) return "var(--accent-green)"
  if (score >= 0.5) return "var(--accent-orange)"
  return "#ff4444"
}

export const SEX_COLORS: Record<string, string> = {
  M: "#4488ff",
  F: "#ff6688",
  U: "#ffaa44",
}
