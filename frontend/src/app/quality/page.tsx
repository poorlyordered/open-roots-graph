"use client"

import { useEffect, useState, useCallback } from "react"
import type { QualityScoreItem, QualitySummary, Conflict, ResearchTaskItem } from "@/lib/types"
import { getQualityScores, getConflicts, getTasks, patchConflict } from "@/lib/api"
import { getScoreColor, SEX_COLORS } from "@/lib/colors"

const fieldLabels: Record<string, string> = {
  birth_date: "Birth Date",
  birth_place: "Birth Place",
  death_date: "Death Date",
  death_place: "Death Place",
  burial_place: "Burial",
  parents: "Parents",
  sources: "Sources",
}

const severityColors: Record<string, string> = {
  critical: "#ff4444",
  high: "#ff8844",
  medium: "#ffaa44",
  low: "#88cc88",
}

const statusColors: Record<string, string> = {
  open: "#ff6688",
  resolved: "#44cc88",
  deferred: "#888",
}

type SortKey = "priority_score" | "completeness_pct" | "name" | "surname" | "source_count" | "conflict_count" | "missing_count" | "birth_year"
type ActiveFilter = "all" | "quick-wins" | "unsourced" | "missing-field"

const PAGE_SIZE = 50

export default function QualityPage() {
  // Quality scores state
  const [rows, setRows] = useState<QualityScoreItem[]>([])
  const [summary, setSummary] = useState<QualitySummary | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [sortBy, setSortBy] = useState<SortKey>("priority_score")
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc")
  const [search, setSearch] = useState("")
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>("all")
  const [missingField, setMissingField] = useState("")
  const [loading, setLoading] = useState(true)

  // Conflicts & tasks state (existing)
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [tasks, setTasks] = useState<ResearchTaskItem[]>([])
  const [severityFilter, setSeverityFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  const loadScores = useCallback(() => {
    setLoading(true)
    const params: Record<string, unknown> = {
      sort_by: sortBy,
      sort_dir: sortDir,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }
    if (search) params.search = search
    if (activeFilter === "quick-wins") params.max_missing = 1
    if (activeFilter === "unsourced") params.unsourced_only = true
    if (activeFilter === "missing-field" && missingField) params.missing_field = missingField

    getQualityScores(params as Parameters<typeof getQualityScores>[0])
      .then((res) => {
        setRows(res.data || [])
        setSummary(res.summary || null)
        setTotal(res.meta?.total || 0)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [sortBy, sortDir, page, search, activeFilter, missingField])

  useEffect(() => { loadScores() }, [loadScores])

  // Reset page when filters change
  useEffect(() => { setPage(0) }, [search, activeFilter, missingField, sortBy, sortDir])

  // Load conflicts and tasks
  useEffect(() => {
    getConflicts({
      severity: severityFilter || undefined,
      status: statusFilter || undefined,
    }).then((d) => setConflicts(d.data)).catch(() => {})
  }, [severityFilter, statusFilter])

  useEffect(() => {
    getTasks().then((d) => setTasks(d.data)).catch(() => {})
  }, [])

  const handleConflictUpdate = async (id: string, status: string, resolution?: string | null) => {
    await patchConflict(id, { status, resolution })
    setConflicts((prev) => prev.map((c) =>
      c.id === id ? { ...c, status, resolution: resolution ?? c.resolution } : c
    ))
  }

  const toggleSort = (key: SortKey) => {
    if (sortBy === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"))
    } else {
      setSortBy(key)
      setSortDir(key === "completeness_pct" || key === "missing_count" ? "asc" : "asc")
    }
  }

  const sortArrow = (key: SortKey) =>
    sortBy === key ? (sortDir === "asc" ? " ▲" : " ▼") : ""

  const setFilter = (filter: ActiveFilter, field?: string) => {
    if (activeFilter === filter && filter !== "missing-field") {
      setActiveFilter("all")
      setMissingField("")
    } else if (filter === "missing-field" && missingField === field) {
      setActiveFilter("all")
      setMissingField("")
    } else {
      setActiveFilter(filter)
      if (field) setMissingField(field)
      else setMissingField("")
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const completenessColor = (pct: number) => {
    if (pct >= 80) return "var(--accent-green)"
    if (pct >= 50) return "var(--accent-orange)"
    return "#ff4444"
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-bold mb-1">Data Quality</h1>
      <p className="text-sm mb-6" style={{ color: "#888" }}>
        Individual completeness scores, missing data, and evidence conflicts
      </p>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "Individuals", value: summary.total_individuals, color: "var(--accent)" },
            {
              label: "Avg Completeness",
              value: `${Math.round(summary.avg_completeness)}%`,
              color: completenessColor(summary.avg_completeness),
            },
            { label: "Fully Complete", value: summary.fully_complete, color: "var(--accent-green)" },
            {
              label: "Quick Wins",
              value: summary.quick_win_count,
              color: "var(--accent-orange)",
              onClick: () => setFilter("quick-wins"),
              active: activeFilter === "quick-wins",
            },
            {
              label: "Unsourced",
              value: summary.unsourced_count,
              color: "#ff4444",
              onClick: () => setFilter("unsourced"),
              active: activeFilter === "unsourced",
            },
          ].map((c) => (
            <div
              key={c.label}
              className="rounded-xl p-4 border transition-colors"
              style={{
                background: "var(--surface)",
                borderColor: ("active" in c && c.active) ? c.color : "var(--border)",
                cursor: "onClick" in c ? "pointer" : "default",
              }}
              onClick={"onClick" in c ? c.onClick : undefined}
            >
              <div className="text-2xl font-bold" style={{ color: c.color }}>{c.value}</div>
              <div className="text-xs mt-1" style={{ color: "#888" }}>{c.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Per-field completeness bars (clickable) */}
      {summary && Object.keys(summary.completeness_by_field).length > 0 && (
        <div className="rounded-xl p-4 border mb-6"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <h2 className="text-sm font-semibold mb-3" style={{ color: "#888" }}>
            Completeness by Field
            <span className="font-normal ml-2" style={{ color: "#555" }}>click to filter table</span>
          </h2>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(summary.completeness_by_field).map(([key, pct]) => {
              const isActive = activeFilter === "missing-field" && missingField === key
              return (
                <div
                  key={key}
                  className="cursor-pointer rounded-lg p-2 transition-colors"
                  style={{
                    background: isActive ? "rgba(68,136,255,0.1)" : "transparent",
                    border: isActive ? "1px solid var(--accent)" : "1px solid transparent",
                  }}
                  onClick={() => setFilter("missing-field", key)}
                >
                  <div className="flex justify-between text-xs mb-1">
                    <span>{fieldLabels[key] || key.replace(/_/g, " ")}</span>
                    <span style={{ color: completenessColor(pct) }}>{pct}%</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "#1a1a3a" }}>
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, background: completenessColor(pct) }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Active filter chip */}
      {activeFilter !== "all" && (
        <div className="flex items-center gap-2 mb-4">
          <span className="text-xs" style={{ color: "#888" }}>Filtered:</span>
          <span
            className="text-[11px] px-2 py-1 rounded-lg cursor-pointer"
            style={{ background: "rgba(68,136,255,0.15)", color: "var(--accent)" }}
            onClick={() => setFilter("all")}
          >
            {activeFilter === "quick-wins" && "Missing 1 field"}
            {activeFilter === "unsourced" && "No sources"}
            {activeFilter === "missing-field" && `Missing ${fieldLabels[missingField] || missingField}`}
            {" "}✕
          </span>
        </div>
      )}

      {/* Individual Quality Scorecard Table */}
      <div
        className="rounded-xl border mb-6"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <h3 className="text-sm font-semibold" style={{ color: "#888" }}>
            Individual Scores
            <span className="ml-2 font-normal" style={{ color: "#555" }}>
              {total.toLocaleString()} records
            </span>
          </h3>
          <input
            type="text"
            placeholder="Search name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1 rounded-lg text-xs border w-48"
            style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
          />
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-[11px]" style={{ color: "#666" }}>
                {([
                  ["priority_score", "Priority"],
                  ["name", "Name"],
                  ["surname", "Surname"],
                  ["completeness_pct", "Completeness"],
                  ["missing_count", "Missing"],
                  ["source_count", "Sources"],
                  ["conflict_count", "Conflicts"],
                  ["birth_year", "Born"],
                ] as [SortKey, string][]).map(([key, label]) => (
                  <th
                    key={key}
                    className="px-3 py-2 font-medium cursor-pointer select-none"
                    onClick={() => toggleSort(key)}
                    style={{ borderBottom: "1px solid var(--border)" }}
                  >
                    {label}{sortArrow(key)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center" style={{ color: "#555" }}>
                    Scoring individuals...
                  </td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center" style={{ color: "#555" }}>
                    No records found
                  </td>
                </tr>
              ) : (
                rows.map((r) => (
                  <tr
                    key={r.id}
                    style={{ borderBottom: "1px solid var(--border)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface-hover)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    <td className="px-3 py-2 text-center">
                      <span
                        className="text-sm font-bold"
                        style={{
                          color: r.priority_score >= 70 ? "#ff4444"
                            : r.priority_score >= 40 ? "var(--accent-orange)"
                            : "var(--accent-green)",
                        }}
                      >
                        {Math.round(r.priority_score)}
                      </span>
                      {r.is_brick_wall && (
                        <span className="block text-[8px] font-semibold" style={{ color: "#ff4444" }}>
                          WALL
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span className="font-medium">{r.name}</span>
                      <span className="ml-1.5 text-[10px]" style={{ color: SEX_COLORS[r.sex || "U"] || "#888" }}>
                        {r.sex === "M" ? "M" : r.sex === "F" ? "F" : ""}
                      </span>
                    </td>
                    <td className="px-3 py-2" style={{ color: "var(--accent)" }}>{r.surname || "—"}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: "#1a1a3a" }}>
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${r.completeness_pct}%`,
                              background: completenessColor(r.completeness_pct),
                            }}
                          />
                        </div>
                        <span className="text-[11px] w-8" style={{ color: completenessColor(r.completeness_pct) }}>
                          {Math.round(r.completeness_pct)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      {r.missing_fields.length > 0 ? (
                        <div className="flex flex-wrap gap-0.5">
                          {r.missing_fields.map((f) => (
                            <span
                              key={f}
                              className="text-[9px] px-1 py-0.5 rounded"
                              style={{ background: "rgba(255,68,68,0.1)", color: "#cc6666" }}
                            >
                              {fieldLabels[f] || f}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[10px]" style={{ color: "var(--accent-green)" }}>Complete</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center" style={{
                      color: r.source_count > 0 ? "var(--foreground)" : "#ff4444",
                    }}>
                      {r.source_count}
                    </td>
                    <td className="px-3 py-2 text-center" style={{
                      color: r.conflict_count > 0 ? "var(--accent-orange)" : "#444",
                    }}>
                      {r.conflict_count}
                    </td>
                    <td className="px-3 py-2" style={{ color: r.birth_year ? "var(--foreground)" : "#444" }}>
                      {r.birth_year || "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t" style={{ borderColor: "var(--border)" }}>
            <span className="text-xs" style={{ color: "#555" }}>
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total.toLocaleString()}
            </span>
            <div className="flex gap-1">
              {[
                { label: "First", go: 0, disabled: page === 0 },
                { label: "Prev", go: Math.max(0, page - 1), disabled: page === 0 },
              ].map((b) => (
                <button
                  key={b.label}
                  onClick={() => setPage(b.go)}
                  disabled={b.disabled}
                  className="px-2 py-1 rounded text-xs border"
                  style={{
                    background: "transparent",
                    borderColor: "var(--border)",
                    color: b.disabled ? "#333" : "var(--foreground)",
                  }}
                >
                  {b.label}
                </button>
              ))}
              <span className="px-3 py-1 text-xs" style={{ color: "#888" }}>
                {page + 1} / {totalPages}
              </span>
              {[
                { label: "Next", go: Math.min(totalPages - 1, page + 1), disabled: page >= totalPages - 1 },
                { label: "Last", go: totalPages - 1, disabled: page >= totalPages - 1 },
              ].map((b) => (
                <button
                  key={b.label}
                  onClick={() => setPage(b.go)}
                  disabled={b.disabled}
                  className="px-2 py-1 rounded text-xs border"
                  style={{
                    background: "transparent",
                    borderColor: "var(--border)",
                    color: b.disabled ? "#333" : "var(--foreground)",
                  }}
                >
                  {b.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Conflicts List */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Conflicts</h2>
          <div className="flex gap-2">
            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}
              className="text-xs px-2 py-1 rounded border"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--foreground)" }}>
              <option value="">All severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs px-2 py-1 rounded border"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--foreground)" }}>
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="resolved">Resolved</option>
              <option value="deferred">Deferred</option>
            </select>
          </div>
        </div>

        <div className="space-y-2">
          {conflicts.map((c) => (
            <div key={c.id} className="rounded-lg p-3 border"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                      style={{ background: severityColors[c.severity] + "22", color: severityColors[c.severity] }}>
                      {c.severity.toUpperCase()}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{ background: statusColors[c.status] + "22", color: statusColors[c.status] }}>
                      {c.status}
                    </span>
                    <span className="text-[10px]" style={{ color: "#555" }}>{c.field}</span>
                  </div>
                  <p className="text-sm">{c.description}</p>
                  {c.resolution && (
                    <p className="text-xs mt-1" style={{ color: "var(--accent-green)" }}>
                      Resolution: {c.resolution}
                    </p>
                  )}
                  {c.individuals.length > 0 && (
                    <div className="flex gap-2 mt-1.5 flex-wrap">
                      {c.individuals.map((i) => (
                        <span key={i.id} className="text-[11px] px-2 py-0.5 rounded"
                          style={{ background: "var(--surface-hover)", color: "var(--accent)" }}>
                          {i.name} {i.birth_year ? `(b.${i.birth_year})` : ""}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                {c.status === "open" && (
                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() => {
                        const res = prompt("Resolution note:")
                        if (res !== null) handleConflictUpdate(c.id, "resolved", res)
                      }}
                      className="text-[10px] px-2 py-1 rounded"
                      style={{ background: "var(--accent-green)", color: "#000" }}>
                      Resolve
                    </button>
                    <button
                      onClick={() => handleConflictUpdate(c.id, "deferred", null)}
                      className="text-[10px] px-2 py-1 rounded"
                      style={{ background: "#333", color: "#888" }}>
                      Defer
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Research Tasks */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Research Tasks</h2>
        <div className="space-y-2">
          {tasks.map((t) => (
            <div key={t.id} className="rounded-lg p-3 border"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                  style={{ background: severityColors[t.priority] + "22", color: severityColors[t.priority] }}>
                  {t.priority}
                </span>
                <span className="text-[10px]" style={{ color: "#555" }}>{t.status}</span>
              </div>
              <p className="text-sm font-medium">{t.title}</p>
              <p className="text-xs mt-1" style={{ color: "#888" }}>{t.description}</p>
              {t.target_name && (
                <span className="text-[11px] mt-1.5 inline-block px-2 py-0.5 rounded"
                  style={{ background: "var(--surface-hover)", color: "var(--accent)" }}>
                  {t.target_name}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
