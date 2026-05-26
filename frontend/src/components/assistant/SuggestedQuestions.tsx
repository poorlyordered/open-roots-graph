"use client"

import { useEffect, useState } from "react"
import type { Suggestion, ChatMode } from "@/lib/types"
import { getSuggestions } from "@/lib/api"

interface Props {
  onSelect: (text: string, mode: ChatMode) => void
}

const modeColors: Record<string, string> = {
  query: "var(--accent)",
  hypothesis: "var(--accent-orange)",
  research: "var(--accent-pink)",
}

const modeLabels: Record<string, string> = {
  query: "Query",
  hypothesis: "Hypothesis",
  research: "Research",
}

export default function SuggestedQuestions({ onSelect }: Props) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])

  useEffect(() => {
    getSuggestions()
      .then((res) => setSuggestions(res.data || []))
      .catch(() => {})
  }, [])

  const grouped: Record<string, Suggestion[]> = {}
  for (const s of suggestions) {
    if (!grouped[s.mode]) grouped[s.mode] = []
    grouped[s.mode].push(s)
  }

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([mode, items]) => (
        <div key={mode}>
          <h3
            className="text-xs font-semibold mb-2 uppercase tracking-wider"
            style={{ color: modeColors[mode] || "#888" }}
          >
            {modeLabels[mode] || mode}
          </h3>
          <div className="flex flex-wrap gap-2">
            {items.map((s, i) => (
              <button
                key={i}
                onClick={() => onSelect(s.text, s.mode as ChatMode)}
                className="text-sm px-3 py-1.5 rounded-full border transition-colors"
                style={{
                  borderColor: modeColors[s.mode] + "44",
                  color: modeColors[s.mode],
                  background: modeColors[s.mode] + "0a",
                }}
              >
                {s.text}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
