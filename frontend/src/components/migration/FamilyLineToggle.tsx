"use client"

import type { FamilyLine } from "@/lib/types"

interface Props {
  familyLines: FamilyLine[]
  activeSurnames: Set<string>
  onToggle: (surname: string) => void
  onSelectAll: () => void
  onSelectNone: () => void
}

export default function FamilyLineToggle({
  familyLines,
  activeSurnames,
  onToggle,
  onSelectAll,
  onSelectNone,
}: Props) {
  return (
    <div
      className="rounded-xl border p-3 overflow-y-auto"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
        maxHeight: "400px",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold" style={{ color: "#888" }}>
          Family Lines
        </span>
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="text-[10px] px-2 py-0.5 rounded"
            style={{ color: "var(--accent)" }}
          >
            All
          </button>
          <button
            onClick={onSelectNone}
            className="text-[10px] px-2 py-0.5 rounded"
            style={{ color: "#888" }}
          >
            None
          </button>
        </div>
      </div>

      {familyLines.map((line) => (
        <label
          key={line.surname}
          className="flex items-center gap-2 py-1 cursor-pointer text-sm"
        >
          <input
            type="checkbox"
            checked={activeSurnames.has(line.surname)}
            onChange={() => onToggle(line.surname)}
            className="rounded"
          />
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ background: line.color || "#888" }}
          />
          <span className="flex-1">{line.surname}</span>
          <span className="text-xs" style={{ color: "#666" }}>
            {line.count}
          </span>
        </label>
      ))}
    </div>
  )
}
