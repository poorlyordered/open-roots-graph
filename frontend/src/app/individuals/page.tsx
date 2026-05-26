"use client"

import { useEffect, useState } from "react"
import type { Individual, IndividualDetail, QualityScoreItem } from "@/lib/types"
import { getIndividuals, getIndividual, getQualityScores } from "@/lib/api"
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

export default function IndividualsPage() {
  const [individuals, setIndividuals] = useState<Individual[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<IndividualDetail | null>(null)
  const [quality, setQuality] = useState<QualityScoreItem | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const limit = 50

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const res = await getIndividuals({
          search: search || undefined,
          limit,
          offset: page * limit,
        })
        setIndividuals(res.data)
        setTotal(res.meta?.total || 0)
      } catch {
        // ignore
      } finally {
        setLoading(false)
      }
    }
    const timer = setTimeout(load, search ? 300 : 0)
    return () => clearTimeout(timer)
  }, [search, page])

  const handleSelect = async (id: string) => {
    if (selectedId === id) {
      setSelectedId(null)
      setDetail(null)
      setQuality(null)
      return
    }
    setSelectedId(id)
    setDetailLoading(true)
    try {
      const [detailRes, qualityRes] = await Promise.all([
        getIndividual(id),
        getQualityScores({ search: "", limit: 1, offset: 0 }).then(() => null).catch(() => null),
      ])
      setDetail(detailRes.data || null)

      // Fetch quality score for this specific individual
      const qRes = await getQualityScores({ search: detailRes.data?.name || "", limit: 20 })
      const match = qRes.data?.find((q: QualityScoreItem) => q.id === id) || null
      setQuality(match)
    } catch {
      setDetail(null)
      setQuality(null)
    } finally {
      setDetailLoading(false)
    }
  }

  const priorityColor = (score: number) =>
    score >= 70 ? "#ff4444" : score >= 40 ? "var(--accent-orange)" : "var(--accent-green)"

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-bold">Individuals</h1>
        <span className="text-sm" style={{ color: "#888" }}>
          {total} total
        </span>
      </div>

      <input
        type="text"
        placeholder="Search by name..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value)
          setPage(0)
        }}
        className="w-full px-4 py-2 rounded-lg text-sm border mb-4"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          color: "var(--foreground)",
        }}
      />

      <div
        className="rounded-xl border overflow-hidden"
        style={{ borderColor: "var(--border)" }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr style={{ background: "var(--surface)" }}>
              <th className="text-left px-4 py-2 font-medium" style={{ color: "#888" }}>Name</th>
              <th className="text-left px-4 py-2 font-medium" style={{ color: "#888" }}>Surname</th>
              <th className="text-left px-4 py-2 font-medium" style={{ color: "#888" }}>Born</th>
              <th className="text-left px-4 py-2 font-medium" style={{ color: "#888" }}>Died</th>
              <th className="text-left px-4 py-2 font-medium" style={{ color: "#888" }}>Sex</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center" style={{ color: "#666" }}>
                  Loading...
                </td>
              </tr>
            ) : individuals.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center" style={{ color: "#666" }}>
                  No results found
                </td>
              </tr>
            ) : (
              individuals.map((i) => (
                <>
                  <tr
                    key={i.id}
                    className="border-t transition-colors cursor-pointer"
                    style={{
                      borderColor: "var(--border)",
                      background: selectedId === i.id ? "var(--surface-hover)" : "transparent",
                    }}
                    onClick={() => handleSelect(i.id)}
                  >
                    <td className="px-4 py-2">{i.name}</td>
                    <td className="px-4 py-2" style={{ color: "var(--accent)" }}>
                      {i.surname || "—"}
                    </td>
                    <td className="px-4 py-2">{i.birth_date_raw || i.birth_year || "—"}</td>
                    <td className="px-4 py-2">{i.death_date_raw || i.death_year || "—"}</td>
                    <td className="px-4 py-2">
                      <span style={{ color: SEX_COLORS[i.sex || "U"] || "#888" }}>
                        {i.sex === "M" ? "Male" : i.sex === "F" ? "Female" : "—"}
                      </span>
                    </td>
                  </tr>

                  {/* Detail Panel */}
                  {selectedId === i.id && (
                    <tr key={`${i.id}-detail`}>
                      <td colSpan={5} className="px-0 py-0">
                        <div
                          className="p-4 border-t"
                          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                        >
                          {detailLoading ? (
                            <div className="text-center py-4" style={{ color: "#555" }}>Loading details...</div>
                          ) : detail ? (
                            <div className="grid grid-cols-3 gap-6">
                              {/* Column 1: Quality Scorecard */}
                              <div>
                                <h3 className="text-xs font-semibold mb-3" style={{ color: "#888" }}>
                                  Quality Score
                                </h3>
                                {quality ? (
                                  <>
                                    <div className="flex items-center gap-4 mb-3">
                                      <div className="text-center">
                                        <div
                                          className="text-2xl font-bold"
                                          style={{ color: priorityColor(quality.priority_score) }}
                                        >
                                          {Math.round(quality.priority_score)}
                                        </div>
                                        <div className="text-[10px]" style={{ color: "#666" }}>Priority</div>
                                      </div>
                                      <div className="flex-1">
                                        <div className="flex justify-between text-[10px] mb-1">
                                          <span style={{ color: "#666" }}>Completeness</span>
                                          <span style={{ color: getScoreColor(quality.completeness_pct / 100) }}>
                                            {Math.round(quality.completeness_pct)}%
                                          </span>
                                        </div>
                                        <div className="h-2 rounded-full overflow-hidden" style={{ background: "#1a1a3a" }}>
                                          <div
                                            className="h-full rounded-full"
                                            style={{
                                              width: `${quality.completeness_pct}%`,
                                              background: getScoreColor(quality.completeness_pct / 100),
                                            }}
                                          />
                                        </div>
                                      </div>
                                    </div>

                                    {quality.is_brick_wall && (
                                      <div
                                        className="text-[10px] px-2 py-1 rounded mb-2 inline-block font-semibold"
                                        style={{ background: "rgba(255,68,68,0.15)", color: "#ff4444" }}
                                      >
                                        BRICK WALL — No known parents
                                      </div>
                                    )}

                                    <div className="flex items-center gap-3 text-[11px] mb-3" style={{ color: "#666" }}>
                                      <span>{quality.source_count} source{quality.source_count !== 1 ? "s" : ""}</span>
                                      {quality.conflict_count > 0 && (
                                        <span style={{ color: "var(--accent-orange)" }}>
                                          {quality.conflict_count} conflict{quality.conflict_count !== 1 ? "s" : ""}
                                        </span>
                                      )}
                                    </div>

                                    {quality.missing_fields.length > 0 && (
                                      <div>
                                        <div className="text-[10px] mb-1" style={{ color: "#666" }}>Missing:</div>
                                        <div className="flex flex-wrap gap-1">
                                          {quality.missing_fields.map((f) => (
                                            <span
                                              key={f}
                                              className="text-[10px] px-1.5 py-0.5 rounded"
                                              style={{ background: "rgba(255,68,68,0.1)", color: "#cc6666" }}
                                            >
                                              {fieldLabels[f] || f}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {quality.missing_fields.length === 0 && (
                                      <div className="text-[11px]" style={{ color: "var(--accent-green)" }}>
                                        All fields complete
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <div className="text-xs" style={{ color: "#555" }}>No score data</div>
                                )}
                              </div>

                              {/* Column 2: Bio Details */}
                              <div>
                                <h3 className="text-xs font-semibold mb-3" style={{ color: "#888" }}>
                                  Details
                                </h3>
                                <div className="space-y-1.5 text-xs">
                                  {detail.birth_place && (
                                    <div>
                                      <span style={{ color: "#666" }}>Birth Place: </span>
                                      {detail.birth_place}
                                    </div>
                                  )}
                                  {detail.death_place && (
                                    <div>
                                      <span style={{ color: "#666" }}>Death Place: </span>
                                      {detail.death_place}
                                    </div>
                                  )}
                                  {detail.burial_place && (
                                    <div>
                                      <span style={{ color: "#666" }}>Burial: </span>
                                      {detail.burial_place}
                                    </div>
                                  )}
                                  {detail.sources.length > 0 && (
                                    <div>
                                      <span style={{ color: "#666" }}>Sources: </span>
                                      {detail.sources.join(", ")}
                                    </div>
                                  )}
                                  {detail.residences.length > 0 && (
                                    <div>
                                      <div style={{ color: "#666" }}>Residences:</div>
                                      {detail.residences.map((r, idx) => (
                                        <div key={idx} className="ml-2" style={{ color: "#aaa" }}>
                                          {r.place}{r.year ? ` (${r.year})` : ""}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  <div className="pt-1 text-[10px]" style={{ color: "#444" }}>
                                    {detail.id}
                                  </div>
                                </div>
                              </div>

                              {/* Column 3: Family */}
                              <div>
                                <h3 className="text-xs font-semibold mb-3" style={{ color: "#888" }}>
                                  Family
                                </h3>
                                <div className="space-y-3 text-xs">
                                  {detail.parents.length > 0 && (
                                    <div>
                                      <div className="text-[10px] mb-1" style={{ color: "#666" }}>Parents</div>
                                      {detail.parents.map((p) => (
                                        <div key={p.id} style={{ color: "var(--accent)" }}>
                                          {p.name}
                                          {p.birth_year ? <span style={{ color: "#555" }}> b.{p.birth_year}</span> : ""}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  {detail.spouses.length > 0 && (
                                    <div>
                                      <div className="text-[10px] mb-1" style={{ color: "#666" }}>Spouses</div>
                                      {detail.spouses.map((s) => (
                                        <div key={s.id} style={{ color: "var(--accent-pink)" }}>
                                          {s.name}
                                          {s.birth_year ? <span style={{ color: "#555" }}> b.{s.birth_year}</span> : ""}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  {detail.children.length > 0 && (
                                    <div>
                                      <div className="text-[10px] mb-1" style={{ color: "#666" }}>
                                        Children ({detail.children.length})
                                      </div>
                                      {detail.children.map((c) => (
                                        <div key={c.id} style={{ color: "var(--accent-green)" }}>
                                          {c.name}
                                          {c.birth_year ? <span style={{ color: "#555" }}> b.{c.birth_year}</span> : ""}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                  {detail.parents.length === 0 && detail.spouses.length === 0 && detail.children.length === 0 && (
                                    <div style={{ color: "#555" }}>No family connections</div>
                                  )}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <div className="text-center py-4" style={{ color: "#555" }}>
                              Could not load details
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-between mt-4">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="px-4 py-1.5 rounded-lg text-sm border disabled:opacity-30"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--foreground)",
            }}
          >
            Previous
          </button>
          <span className="text-sm" style={{ color: "#888" }}>
            Page {page + 1} of {Math.ceil(total / limit)}
          </span>
          <button
            disabled={(page + 1) * limit >= total}
            onClick={() => setPage((p) => p + 1)}
            className="px-4 py-1.5 rounded-lg text-sm border disabled:opacity-30"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--foreground)",
            }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
