"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import type { GraphNode, GraphLink } from "@/lib/types"
import { getGraphData } from "@/lib/api"

const colorMap: Record<number, string> = {
  1: "#4488ff",  // Male
  2: "#ff6688",  // Female
  3: "#88cc88",  // Unknown
  4: "#ffaa44",  // Family
}

export default function GraphPage() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [search, setSearch] = useState("")
  const [surnameFilter, setSurnameFilter] = useState("")
  const [surnames, setSurnames] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const data = await getGraphData()
        const nodes = data.nodes as GraphNode[]
        const links = data.links as GraphLink[]

        const uniqueSurnames = [
          ...new Set(nodes.filter((n) => n.surname).map((n) => n.surname!)),
        ].sort()
        setSurnames(uniqueSurnames)

        renderGraph(nodes, links)
      } catch (err) {
        console.error("Failed to load graph:", err)
      } finally {
        setLoading(false)
      }
    }
    load()

    return () => {
      simulationRef.current?.stop()
    }
  }, [])

  function renderGraph(nodes: GraphNode[], links: GraphLink[]) {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight

    const g = svg.append("g")

    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 8])
        .on("zoom", (event) => g.attr("transform", event.transform))
    )

    const simulation = d3
      .forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        d3.forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id)
          .distance((d) => ((d as GraphLink).type === "CHILD_OF" ? 80 : 50))
          .strength(0.3)
      )
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d) => ((d as GraphNode).type === "family" ? 8 : 14)))

    simulationRef.current = simulation

    const link = g
      .append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => (d.type === "SPOUSE_IN" ? "#666" : "#444"))
      .attr("stroke-width", (d) => (d.type === "SPOUSE_IN" ? 1.5 : 1))
      .attr("stroke-dasharray", (d) => (d.type === "CHILD_OF" ? "4,3" : "none"))
      .attr("opacity", 0.6)

    const node = g
      .append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on("drag", (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )

    // Individual circles
    node
      .filter((d) => d.type === "individual")
      .append("circle")
      .attr("r", 8)
      .attr("fill", (d) => colorMap[d.group] || "#888")
      .attr("stroke", "#222")
      .attr("stroke-width", 1.5)

    // Family diamonds
    node
      .filter((d) => d.type === "family")
      .append("rect")
      .attr("width", 10)
      .attr("height", 10)
      .attr("x", -5)
      .attr("y", -5)
      .attr("transform", "rotate(45)")
      .attr("fill", colorMap[4])
      .attr("stroke", "#222")
      .attr("stroke-width", 1)

    // Labels
    node
      .filter((d) => d.type === "individual")
      .append("text")
      .text((d) => (d.name || "").split(" ").slice(-1)[0])
      .attr("x", 12)
      .attr("y", 4)
      .attr("font-size", "9px")
      .attr("fill", "#999")

    // Tooltips via title
    node.append("title").text((d) => {
      if (d.type === "individual") {
        let t = d.name || "Unknown"
        if (d.birth_date) t += `\nBorn: ${d.birth_date}`
        if (d.death_date) t += `\nDied: ${d.death_date}`
        return t
      }
      return d.label || "Family"
    })

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => ((d.source as GraphNode).x || 0))
        .attr("y1", (d) => ((d.source as GraphNode).y || 0))
        .attr("x2", (d) => ((d.target as GraphNode).x || 0))
        .attr("y2", (d) => ((d.target as GraphNode).y || 0))

      node.attr("transform", (d) => `translate(${d.x || 0},${d.y || 0})`)
    })
  }

  // Search effect
  useEffect(() => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    const query = search.toLowerCase()

    if (!query && !surnameFilter) {
      svg.selectAll("circle").attr("opacity", 1).attr("r", 8)
      svg.selectAll("rect").attr("opacity", 1)
      svg.selectAll("text").attr("opacity", 1)
      svg.selectAll("line").attr("opacity", 0.6)
      return
    }

    svg.selectAll<SVGCircleElement, GraphNode>("circle").attr("opacity", (d) => {
      if (query && d.name?.toLowerCase().includes(query)) return 1
      if (surnameFilter && d.surname === surnameFilter) return 1
      if (!query && !surnameFilter) return 1
      return 0.1
    })
    svg.selectAll("rect").attr("opacity", 0.1)
    svg.selectAll("line").attr("opacity", 0.05)
  }, [search, surnameFilter])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg" style={{ color: "#666" }}>Loading graph...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div
        className="flex items-center gap-4 p-3 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <input
          type="text"
          placeholder="Search by name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-sm border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--foreground)",
          }}
        />
        <select
          value={surnameFilter}
          onChange={(e) => setSurnameFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-sm border"
          style={{
            background: "var(--surface)",
            borderColor: "var(--border)",
            color: "var(--foreground)",
          }}
        >
          <option value="">All surnames</option>
          {surnames.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

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
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-full inline-block" style={{ background: "#ffaa44" }} />
            Family
          </span>
        </div>
      </div>

      {/* Graph */}
      <svg ref={svgRef} className="flex-1 w-full" style={{ minHeight: "600px" }} />
    </div>
  )
}
