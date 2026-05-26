"use client"

import { useEffect, useState } from "react"
import type {
  Individual,
  ResearchPriorityItem,
  ResearchPrioritySummary,
  RootCandidate,
} from "@/lib/types"
import { getIndividuals, getResearchPriorities, getRootCandidates } from "@/lib/api"
import { getScoreColor } from "@/lib/colors"

const fieldLabels: Record<string, string> = {
  birth_date: "Birth Date",
  birth_place: "Birth Place",
  death_date: "Death Date",
  death_place: "Death Place",
  burial_place: "Burial",
  parents: "Parents",
  sources: "Sources",
}

const confidenceColors: Record<string, string> = {
  verified: "var(--accent-green)",
  high: "#44aacc",
  medium: "var(--accent-orange)",
  low: "#ff4444",
}

export default function ResearchPrioritiesPage() {
  const [search, setSearch] = useState("")
  const [searchResults, setSearchResults] = useState<Individual[]>([])
  const [candidates, setCandidates] = useState<RootCandidate[]>([])
  const [rootId, setRootId] = useState("")
  const [rootName, setRootName] = useState("")
  const [relationship, setRelationship] = useState("all")
  const [items, setItems] = useState<ResearchPriorityItem[]>([])
  const [summary, setSummary] = useState<ResearchPrioritySummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 50

  // Load root candidates on mount
  useEffect(() => {
    getRootCandidates().then((res) => setCandidates(res.data || []))
  }, [])

  // Search individuals
  useEffect(() => {
    if (!search || search.length < 2) {
      setSearchResults([])
      return
    }
    const timer = setTimeout(() => {
      getIndividuals({ search, limit: 15 }).then((res) => setSearchResults(res.data || []))
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  // Load priorities when root changes
  useEffect(() => {
    if (!rootId) return
    setLoading(true)
    setPage(0)
    getResearchPriorities({
      root_id: rootId,
      relationship,
      limit: PAGE_SIZE,
      offset: 0,
    }).then((res) => {
      setItems(res.data || [])
      setSummary(res.summary || null)
      setTotal(res.meta?.total || 0)
      setLoading(false)
    })
  }, [rootId, relationship])

  const loadMore = () => {
    const nextPage = page + 1
    setPage(nextPage)
    getResearchPriorities({
      root_id: rootId,
      relationship,
      limit: PAGE_SIZE,
      offset: nextPage * PAGE_SIZE,
    }).then((res) => {
      setItems((prev) => [...prev, ...(res.data || [])])
    })
  }

  const selectRoot = (id: string, name: string) => {
    setRootId(id)
    setRootName(name)
    setSearch("")
    setSearchResults([])
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-xl font-bold mb-1">Research Priorities</h1>
      <p className="text-sm mb-6" style={{ color: "#888" }}>
        Depth-first research queue — ancestors furthest back with the least evidence rank highest
      </p>

      {/* Root selector */}
      <div className="flex items-start gap-4 mb-6">
        <div className="relative">
          <label className="text-xs block mb-1" style={{ color: "#666" }}>
            Start from individual
          </label>
          <input
            type="text"
            placeholder="Search by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1.5 rounded-lg text-sm border w-72"
            style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
          />
          {searchResults.length > 0 && (
            <div
              className="absolute top-full left-0 w-72 mt-1 rounded-lg border overflow-hidden z-10"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              {searchResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => selectRoot(r.id, r.name)}
                  className="w-full text-left px-3 py-2 text-sm"
                  style={{ color: "var(--foreground)" }}
                >
                  {r.name}
                  {r.birth_year && (
                    <span className="ml-2 text-[11px]" style={{ color: "#666" }}>
                      b.{r.birth_year}
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="text-xs block mb-1" style={{ color: "#666" }}>
            Or pick a suggested root
          </label>
          <select
            value={rootId}
            onChange={(e) => {
              const c = candidates.find((x) => x.id === e.target.value)
              if (c) selectRoot(c.id, c.name)
            }}
            className="px-3 py-1.5 rounded-lg text-sm border"
            style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
          >
            <option value="">Select...</option>
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.descendant_count} descendants)
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs block mb-1" style={{ color: "#666" }}>
            Show
          </label>
          <select
            value={relationship}
            onChange={(e) => setRelationship(e.target.value)}
            className="px-3 py-1.5 rounded-lg text-sm border"
            style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
          >
            <option value="all">All relatives</option>
            <option value="direct">Direct line only</option>
            <option value="collateral">Collateral only</option>
          </select>
        </div>

        {rootName && (
          <div className="pt-4 text-sm">
            Rooted at{" "}
            <span style={{ color: "var(--accent)" }}>{rootName}</span>
          </div>
        )}
      </div>

      {/* Summary cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: "Scored", value: summary.total_scored, color: "var(--accent)" },
            { label: "Direct Line", value: summary.direct_line_count, color: "var(--accent-green)" },
            { label: "Collateral", value: summary.collateral_count, color: "var(--accent-orange)" },
            { label: "Brick Walls", value: summary.brick_walls, color: "#ff4444" },
            {
              label: "Avg Completeness",
              value: `${Math.round(summary.avg_completeness * 100)}%`,
              color: getScoreColor(summary.avg_completeness),
            },
          ].map((c) => (
            <div
              key={c.label}
              className="rounded-xl p-4 border"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="text-2xl font-bold" style={{ color: c.color }}>
                {c.value}
              </div>
              <div className="text-xs mt-1" style={{ color: "#888" }}>
                {c.label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Priority queue */}
      {loading ? (
        <div className="text-center py-12" style={{ color: "#666" }}>
          Scoring ancestors...
        </div>
      ) : !rootId ? (
        <div className="text-center py-12" style={{ color: "#555" }}>
          <div className="text-4xl mb-3">▲</div>
          <p>Select an individual above to generate their research priority queue</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, idx) => (
            <div
              key={item.id}
              className="rounded-lg p-4 border flex items-start gap-4"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              {/* Rank */}
              <div
                className="text-lg font-bold w-8 text-center flex-shrink-0"
                style={{ color: "#444" }}
              >
                {idx + 1}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm">{item.name}</span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                    style={{
                      background:
                        item.relationship === "direct"
                          ? "rgba(68,136,255,0.15)"
                          : "rgba(136,136,136,0.15)",
                      color: item.relationship === "direct" ? "var(--accent)" : "#888",
                    }}
                  >
                    {item.relationship === "direct" ? "DIRECT" : "COLLATERAL"}
                  </span>
                  <span className="text-[10px]" style={{ color: "#555" }}>
                    Gen {item.generation}
                  </span>
                  {item.is_brick_wall && (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                      style={{ background: "rgba(255,68,68,0.15)", color: "#ff4444" }}
                    >
                      BRICK WALL
                    </span>
                  )}
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded"
                    style={{
                      background: confidenceColors[item.confidence_label] + "15",
                      color: confidenceColors[item.confidence_label],
                    }}
                  >
                    {item.confidence_label.toUpperCase()} ({Math.round(item.confidence_value * 100)}%)
                  </span>
                  {item.keystone_score > 0 && (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded font-semibold"
                      style={{ background: "rgba(68,136,255,0.15)", color: "var(--accent)" }}
                    >
                      KEYSTONE +{Math.round(item.keystone_score)}
                    </span>
                  )}
                  {item.has_conflicts && (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{ background: "rgba(255,170,68,0.15)", color: "var(--accent-orange)" }}
                    >
                      {item.conflict_count} conflict{item.conflict_count !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>

                <div className="text-xs" style={{ color: "#666" }}>
                  {item.birth_year ? `b.${item.birth_year}` : "birth unknown"}
                  {item.death_year ? ` — d.${item.death_year}` : ""}
                  {item.source_count > 0 && (
                    <span className="ml-2">{item.source_count} source{item.source_count !== 1 ? "s" : ""}</span>
                  )}
                </div>

                {/* Missing fields */}
                {item.missing_fields.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {item.missing_fields.map((f) => (
                      <span
                        key={f}
                        className="text-[10px] px-1.5 py-0.5 rounded"
                        style={{ background: "rgba(255,68,68,0.1)", color: "#cc6666" }}
                      >
                        {fieldLabels[f] || f}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Scores */}
              <div className="flex items-center gap-4 flex-shrink-0">
                {/* Completeness bar */}
                <div className="w-20">
                  <div className="flex justify-between text-[10px] mb-0.5">
                    <span style={{ color: "#666" }}>Complete</span>
                    <span style={{ color: getScoreColor(item.completeness_score) }}>
                      {Math.round(item.completeness_score * 100)}%
                    </span>
                  </div>
                  <div
                    className="h-1.5 rounded-full overflow-hidden"
                    style={{ background: "#1a1a3a" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${item.completeness_score * 100}%`,
                        background: getScoreColor(item.completeness_score),
                      }}
                    />
                  </div>
                </div>

                {/* Priority score */}
                <div
                  className="text-lg font-bold w-12 text-right"
                  style={{
                    color:
                      item.priority_score >= 70
                        ? "#ff4444"
                        : item.priority_score >= 40
                          ? "var(--accent-orange)"
                          : "var(--accent-green)",
                  }}
                >
                  {Math.round(item.priority_score)}
                </div>
              </div>
            </div>
          ))}

          {/* Load more */}
          {items.length < total && (
            <button
              onClick={loadMore}
              className="w-full py-3 rounded-lg text-sm border mt-2"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "#888" }}
            >
              Load more ({total - items.length} remaining)
            </button>
          )}
        </div>
      )}
    </div>
  )
}
