"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import type { Individual, PedigreeNode } from "@/lib/types"
import { getIndividuals, getPedigree } from "@/lib/api"

const sexColors: Record<string, string> = {
  M: "#4488ff",
  F: "#ff6688",
}

export default function PedigreePage() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [search, setSearch] = useState("")
  const [results, setResults] = useState<Individual[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedName, setSelectedName] = useState("")
  const [depth, setDepth] = useState(5)
  const [tree, setTree] = useState<PedigreeNode | null>(null)
  const [maxGen, setMaxGen] = useState(0)
  const [loading, setLoading] = useState(false)

  // Search individuals
  useEffect(() => {
    if (!search || search.length < 2) {
      setResults([])
      return
    }
    const timer = setTimeout(() => {
      getIndividuals({ search, limit: 15 }).then((res) => setResults(res.data || []))
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  // Load pedigree when selection changes
  useEffect(() => {
    if (!selectedId) return
    setLoading(true)
    getPedigree(selectedId, depth).then((res) => {
      setTree(res.data || null)
      setMaxGen(res.max_generation || 0)
      setLoading(false)
    })
  }, [selectedId, depth])

  // D3 rendering
  useEffect(() => {
    if (!svgRef.current || !tree) return
    renderPedigree(tree)
  }, [tree])

  function renderPedigree(root: PedigreeNode) {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight || 600

    const g = svg.append("g")

    // Zoom
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.2, 4])
        .on("zoom", (event) => g.attr("transform", event.transform)),
    )

    // Build D3 hierarchy
    const hierarchy = d3.hierarchy(root, (d) => d.children)

    const nodeWidth = 180
    const nodeHeight = 60
    const treeLayout = d3.tree<PedigreeNode>().nodeSize([nodeHeight + 20, nodeWidth + 40])

    treeLayout(hierarchy)

    // Center the tree
    const nodes = hierarchy.descendants()
    const yExtent = d3.extent(nodes, (d) => d.x) as [number, number]
    const xExtent = d3.extent(nodes, (d) => d.y) as [number, number]

    const offsetX = width / 4 - (xExtent[0] || 0)
    const offsetY = height / 2 - ((yExtent[0] + yExtent[1]) / 2 || 0)
    g.attr("transform", `translate(${offsetX},${offsetY})`)

    // Links
    g.selectAll("path.link")
      .data(hierarchy.links())
      .join("path")
      .attr("class", "link")
      .attr("d", (d) => {
        const sx = d.source.y ?? 0
        const sy = d.source.x ?? 0
        const tx = d.target.y ?? 0
        const ty = d.target.x ?? 0
        const mx = (sx + tx) / 2
        return `M${sx},${sy} C${mx},${sy} ${mx},${ty} ${tx},${ty}`
      })
      .attr("fill", "none")
      .attr("stroke", "#333")
      .attr("stroke-width", 1.5)

    // Node groups
    const node = g
      .selectAll<SVGGElement, d3.HierarchyPointNode<PedigreeNode>>("g.node")
      .data(nodes)
      .join("g")
      .attr("class", "node")
      .attr("transform", (d) => `translate(${d.y},${d.x})`)

    // Node card background
    node
      .append("rect")
      .attr("x", -nodeWidth / 2)
      .attr("y", -nodeHeight / 2)
      .attr("width", nodeWidth)
      .attr("height", nodeHeight)
      .attr("rx", 8)
      .attr("fill", "#0d0d20")
      .attr("stroke", (d) => sexColors[d.data.sex || ""] || "#444")
      .attr("stroke-width", (d) => (d.data.id === root.id ? 2 : 1))

    // Generation indicator (left border)
    node
      .append("rect")
      .attr("x", -nodeWidth / 2)
      .attr("y", -nodeHeight / 2)
      .attr("width", 4)
      .attr("height", nodeHeight)
      .attr("rx", 2)
      .attr("fill", (d) => sexColors[d.data.sex || ""] || "#444")

    // Name
    node
      .append("text")
      .attr("x", -nodeWidth / 2 + 14)
      .attr("y", -6)
      .attr("fill", "#ddd")
      .attr("font-size", "12px")
      .attr("font-weight", "600")
      .text((d) => {
        const name = d.data.name || "Unknown"
        return name.length > 22 ? name.slice(0, 22) + "…" : name
      })

    // Years
    node
      .append("text")
      .attr("x", -nodeWidth / 2 + 14)
      .attr("y", 12)
      .attr("fill", "#888")
      .attr("font-size", "10px")
      .text((d) => {
        const b = d.data.birth_year ? String(d.data.birth_year) : "?"
        const death = d.data.death_year ? String(d.data.death_year) : "?"
        return `${b} — ${death}`
      })

    // Place
    node
      .append("text")
      .attr("x", -nodeWidth / 2 + 14)
      .attr("y", 24)
      .attr("fill", "#555")
      .attr("font-size", "9px")
      .text((d) => {
        const place = d.data.birth_place || d.data.death_place || ""
        return place.length > 28 ? place.slice(0, 28) + "…" : place
      })

    // Generation badge
    node
      .append("text")
      .attr("x", nodeWidth / 2 - 10)
      .attr("y", -nodeHeight / 2 + 14)
      .attr("text-anchor", "end")
      .attr("fill", "#444")
      .attr("font-size", "9px")
      .text((d) => `G${d.data.generation}`)

    // Click to re-root
    node.style("cursor", "pointer").on("click", (_event, d) => {
      if (d.data.id !== selectedId) {
        setSelectedId(d.data.id)
        setSelectedName(d.data.name)
        setSearch("")
        setResults([])
      }
    })

    // Tooltip
    node.append("title").text((d) => {
      let t = d.data.name
      if (d.data.birth_year) t += `\nBorn: ${d.data.birth_year}`
      if (d.data.birth_place) t += ` at ${d.data.birth_place}`
      if (d.data.death_year) t += `\nDied: ${d.data.death_year}`
      if (d.data.death_place) t += ` at ${d.data.death_place}`
      return t
    })
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div
        className="flex items-center gap-4 p-3 border-b flex-shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <div className="relative">
          <input
            type="text"
            placeholder="Search for a person..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="px-3 py-1.5 rounded-lg text-sm border w-64"
            style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
          />
          {results.length > 0 && (
            <div
              className="absolute top-full left-0 w-64 mt-1 rounded-lg border overflow-hidden z-10"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              {results.map((r) => (
                <button
                  key={r.id}
                  onClick={() => {
                    setSelectedId(r.id)
                    setSelectedName(r.name)
                    setSearch("")
                    setResults([])
                  }}
                  className="w-full text-left px-3 py-2 text-sm transition-colors"
                  style={{ color: "var(--foreground)" }}
                >
                  {r.name}
                  {r.birth_year ? (
                    <span className="text-[11px] ml-2" style={{ color: "#666" }}>
                      b.{r.birth_year}
                    </span>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>

        <select
          value={depth}
          onChange={(e) => setDepth(Number(e.target.value))}
          className="px-3 py-1.5 rounded-lg text-sm border"
          style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
        >
          {[3, 4, 5, 6, 7, 8].map((d) => (
            <option key={d} value={d}>
              {d} generations
            </option>
          ))}
        </select>

        {selectedName && (
          <div className="text-sm">
            <span style={{ color: "#888" }}>Showing ancestors of </span>
            <span style={{ color: "var(--accent)" }}>{selectedName}</span>
            {maxGen > 0 && (
              <span className="ml-2 text-xs" style={{ color: "#555" }}>
                ({maxGen} generations found)
              </span>
            )}
          </div>
        )}

        {/* Legend */}
        <div className="ml-auto flex items-center gap-4 text-xs" style={{ color: "#888" }}>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: "#4488ff" }} />
            Male
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: "#ff6688" }} />
            Female
          </span>
        </div>
      </div>

      {/* Chart */}
      {!selectedId ? (
        <div className="flex items-center justify-center flex-1">
          <div className="text-center" style={{ color: "#555" }}>
            <div className="text-4xl mb-3">△</div>
            <p>Search for a person to view their ancestor tree</p>
          </div>
        </div>
      ) : loading ? (
        <div className="flex items-center justify-center flex-1">
          <div style={{ color: "#666" }}>Loading pedigree...</div>
        </div>
      ) : (
        <svg ref={svgRef} className="flex-1 w-full" style={{ minHeight: "600px" }} />
      )}
    </div>
  )
}
