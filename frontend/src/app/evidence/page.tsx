"use client"

import { useEffect, useState } from "react"
import type { Individual, Claim, Conflict } from "@/lib/types"
import { getIndividuals, getClaimsForIndividual, getConflictsForIndividual, patchClaim } from "@/lib/api"
import { getScoreColor } from "@/lib/colors"

const typeLabels: Record<string, string> = {
  name: "Name",
  birth_date: "Birth Date",
  birth_place: "Birth Place",
  death_date: "Death Date",
  death_place: "Death Place",
  burial_place: "Burial Place",
}

const statusIcon = (s: string) =>
  s === "accepted" ? "✓" : s === "rejected" ? "✕" : s === "conflicted" ? "!" : "?"

export default function EvidencePage() {
  const [search, setSearch] = useState("")
  const [results, setResults] = useState<Individual[]>([])
  const [selected, setSelected] = useState<Individual | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [conflicts, setConflicts] = useState<Conflict[]>([])

  // Search individuals
  useEffect(() => {
    if (!search || search.length < 2) {
      setResults([])
      return
    }
    const timer = setTimeout(() => {
      getIndividuals({ search, limit: 20 })
        .then((d) => setResults(d.data || []))
        .catch(() => {})
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  // Load claims and conflicts for selected individual
  useEffect(() => {
    if (!selected) {
      setClaims([])
      setConflicts([])
      return
    }
    Promise.all([
      getClaimsForIndividual(selected.id),
      getConflictsForIndividual(selected.id),
    ]).then(([claimRes, conflictRes]) => {
      setClaims(claimRes.data || [])
      setConflicts(conflictRes.data || [])
    }).catch(() => {})
  }, [selected])

  const handleClaimUpdate = async (claimId: string, status: string) => {
    await patchClaim(claimId, { status })
    setClaims((prev) => prev.map((c) => (c.id === claimId ? { ...c, status } : c)))
  }

  // Group claims by type
  const claimsByType: Record<string, Claim[]> = {}
  for (const c of claims) {
    if (!claimsByType[c.claim_type]) claimsByType[c.claim_type] = []
    claimsByType[c.claim_type].push(c)
  }

  return (
    <div className="flex h-full">
      {/* Left: Search Panel */}
      <div className="w-72 border-r flex flex-col flex-shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
        <div className="p-3 border-b" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-sm font-semibold mb-2">Evidence Board</h2>
          <input
            type="text"
            placeholder="Search for a person..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-3 py-1.5 rounded-lg text-sm border"
            style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
          />
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {results.map((i) => (
            <button
              key={i.id}
              onClick={() => {
                setSelected(i)
                setSearch("")
                setResults([])
              }}
              className="w-full text-left px-3 py-2 rounded-lg text-sm transition-colors mb-0.5"
              style={{
                background: selected?.id === i.id ? "var(--surface-hover)" : "transparent",
                color: selected?.id === i.id ? "var(--accent)" : "var(--foreground)",
              }}
            >
              <div>{i.name}</div>
              <div className="text-[11px]" style={{ color: "#666" }}>
                {i.birth_year ? `b.${i.birth_year}` : ""}
                {i.death_year ? ` - d.${i.death_year}` : ""}
              </div>
            </button>
          ))}
          {!selected && results.length === 0 && search.length < 2 && (
            <p className="text-xs p-3" style={{ color: "#555" }}>
              Search for a person to view their evidence — claims from records with confidence
              scores and conflict flags.
            </p>
          )}
        </div>
      </div>

      {/* Right: Evidence Detail */}
      <div className="flex-1 overflow-y-auto p-6">
        {!selected ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center" style={{ color: "#555" }}>
              <div className="text-4xl mb-3">◆</div>
              <p>Select a person to view their evidence</p>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-xl font-bold">{selected.name}</h1>
                <p className="text-sm" style={{ color: "#888" }}>
                  {selected.birth_year ? `Born ${selected.birth_year}` : ""}
                  {selected.death_year ? ` — Died ${selected.death_year}` : ""}
                  <span className="ml-3" style={{ color: "#555" }}>{selected.id}</span>
                </p>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span>{claims.length} claims</span>
                {conflicts.length > 0 && (
                  <span style={{ color: "#ff4444" }}>{conflicts.length} conflicts</span>
                )}
              </div>
            </div>

            {/* Conflicts */}
            {conflicts.length > 0 && (
              <div className="mb-6">
                <h2 className="text-sm font-semibold mb-2" style={{ color: "#ff6688" }}>
                  Active Conflicts
                </h2>
                <div className="space-y-2">
                  {conflicts.map((c) => (
                    <div key={c.id} className="rounded-lg p-3 border"
                      style={{ background: "rgba(255,68,68,0.05)", borderColor: "rgba(255,68,68,0.2)" }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                          style={{ background: "rgba(255,68,68,0.2)", color: "#ff4444" }}>
                          {c.severity.toUpperCase()}
                        </span>
                        <span className="text-[10px]" style={{ color: "#888" }}>{c.field}</span>
                      </div>
                      <p className="text-sm">{c.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Claims by Type */}
            <div className="space-y-4">
              {Object.entries(claimsByType).map(([type, typeClaims]) => (
                <div key={type} className="rounded-xl border p-4"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                  <h3 className="text-sm font-semibold mb-3" style={{ color: "#888" }}>
                    {typeLabels[type] || type}
                    {typeClaims.length > 1 && (
                      <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded"
                        style={{ background: "rgba(255,170,68,0.2)", color: "var(--accent-orange)" }}>
                        {typeClaims.length} claims
                      </span>
                    )}
                  </h3>
                  <div className="space-y-2">
                    {typeClaims.map((claim) => (
                      <div key={claim.id} className="flex items-center gap-3 py-1.5 px-2 rounded"
                        style={{ background: "rgba(255,255,255,0.02)" }}>
                        {/* Status indicator */}
                        <span className="text-xs w-5 text-center"
                          style={{
                            color: claim.status === "accepted" ? "var(--accent-green)"
                              : claim.status === "rejected" ? "#ff4444" : "var(--accent-orange)",
                          }}>
                          {statusIcon(claim.status)}
                        </span>

                        {/* Value */}
                        <span className="flex-1 text-sm">{claim.value}</span>

                        {/* Confidence bar */}
                        <div className="w-16 flex items-center gap-1">
                          <div className="flex-1 h-1.5 rounded-full overflow-hidden"
                            style={{ background: "#1a1a3a" }}>
                            <div className="h-full rounded-full"
                              style={{
                                width: `${claim.confidence * 100}%`,
                                background: getScoreColor(claim.confidence),
                              }}
                            />
                          </div>
                          <span className="text-[10px] w-7 text-right"
                            style={{ color: getScoreColor(claim.confidence) }}>
                            {Math.round(claim.confidence * 100)}%
                          </span>
                        </div>

                        {/* Source */}
                        <span className="text-[10px] max-w-[150px] truncate"
                          style={{ color: "#555" }}>
                          {claim.record_title || claim.extracted_by || "—"}
                        </span>

                        {/* Actions */}
                        <div className="flex gap-1">
                          {claim.status !== "accepted" && (
                            <button
                              onClick={() => handleClaimUpdate(claim.id, "accepted")}
                              className="text-[10px] px-1.5 py-0.5 rounded"
                              style={{ color: "var(--accent-green)" }}>
                              Accept
                            </button>
                          )}
                          {claim.status !== "rejected" && (
                            <button
                              onClick={() => handleClaimUpdate(claim.id, "rejected")}
                              className="text-[10px] px-1.5 py-0.5 rounded"
                              style={{ color: "#ff4444" }}>
                              Reject
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
