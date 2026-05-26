"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import type { DashboardStats } from "@/lib/types"
import { getDashboardStats } from "@/lib/api"

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const barRef = useRef<SVGSVGElement>(null)
  const histRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    getDashboardStats()
      .then((res) => setStats(res.data))
      .catch(() => {})
  }, [])

  // Surname distribution bar chart
  useEffect(() => {
    if (!barRef.current || !stats) return
    renderSurnameChart(stats.surname_distribution.slice(0, 12))
  }, [stats])

  // Birth decade histogram
  useEffect(() => {
    if (!histRef.current || !stats) return
    renderHistogram(stats.birth_decade_histogram)
  }, [stats])

  function renderSurnameChart(data: { surname: string; count: number }[]) {
    if (!barRef.current) return
    const svg = d3.select(barRef.current)
    svg.selectAll("*").remove()

    const width = barRef.current.clientWidth || 400
    const height = 200
    const margin = { top: 10, right: 10, bottom: 30, left: 70 }

    svg.attr("width", width).attr("height", height)

    const x = d3.scaleLinear()
      .domain([0, d3.max(data, (d) => d.count) || 1])
      .range([margin.left, width - margin.right])

    const y = d3.scaleBand()
      .domain(data.map((d) => d.surname))
      .range([margin.top, height - margin.bottom])
      .padding(0.3)

    svg.selectAll("rect")
      .data(data)
      .join("rect")
      .attr("x", margin.left)
      .attr("y", (d) => y(d.surname) || 0)
      .attr("width", (d) => x(d.count) - margin.left)
      .attr("height", y.bandwidth())
      .attr("fill", "var(--accent)")
      .attr("rx", 3)
      .attr("opacity", 0.7)

    svg.selectAll("text.label")
      .data(data)
      .join("text")
      .attr("class", "label")
      .attr("x", margin.left - 6)
      .attr("y", (d) => (y(d.surname) || 0) + y.bandwidth() / 2 + 4)
      .attr("text-anchor", "end")
      .attr("fill", "#888")
      .attr("font-size", "10px")
      .text((d) => d.surname)

    svg.selectAll("text.count")
      .data(data)
      .join("text")
      .attr("class", "count")
      .attr("x", (d) => x(d.count) + 4)
      .attr("y", (d) => (y(d.surname) || 0) + y.bandwidth() / 2 + 4)
      .attr("fill", "#666")
      .attr("font-size", "10px")
      .text((d) => d.count)
  }

  function renderHistogram(data: { decade: number; count: number }[]) {
    if (!histRef.current) return
    const svg = d3.select(histRef.current)
    svg.selectAll("*").remove()

    const width = histRef.current.clientWidth || 400
    const height = 200
    const margin = { top: 10, right: 10, bottom: 30, left: 30 }

    svg.attr("width", width).attr("height", height)

    const x = d3.scaleBand()
      .domain(data.map((d) => String(d.decade)))
      .range([margin.left, width - margin.right])
      .padding(0.2)

    const y = d3.scaleLinear()
      .domain([0, d3.max(data, (d) => d.count) || 1])
      .range([height - margin.bottom, margin.top])

    svg.selectAll("rect")
      .data(data)
      .join("rect")
      .attr("x", (d) => x(String(d.decade)) || 0)
      .attr("y", (d) => y(d.count))
      .attr("width", x.bandwidth())
      .attr("height", (d) => height - margin.bottom - y(d.count))
      .attr("fill", "var(--accent-green)")
      .attr("rx", 2)
      .attr("opacity", 0.7)

    // X axis labels — show every other century
    const labels = data.filter((d) => d.decade % 100 === 0)
    svg.selectAll("text.axis")
      .data(labels)
      .join("text")
      .attr("class", "axis")
      .attr("x", (d) => (x(String(d.decade)) || 0) + x.bandwidth() / 2)
      .attr("y", height - 8)
      .attr("text-anchor", "middle")
      .attr("fill", "#666")
      .attr("font-size", "10px")
      .text((d) => d.decade)
  }

  const statCards = [
    { label: "Individuals", value: stats?.individuals_count ?? "...", color: "var(--accent)" },
    { label: "Families", value: stats?.families_count ?? "...", color: "var(--accent-pink)" },
    { label: "Places", value: stats?.places_count ?? "...", color: "var(--accent-green)" },
    { label: "Geocoded", value: stats?.geocoded_count ?? "...", color: "var(--accent-orange)" },
  ]

  const features = [
    { href: "/migration", label: "Migration Map", color: "var(--accent)", desc: "Animated geographic movement from the 1500s to present" },
    { href: "/graph", label: "Network Graph", color: "var(--accent-pink)", desc: "Force-directed graph of all family relationships" },
    { href: "/timeline", label: "Timeline", color: "var(--accent-green)", desc: "Vertical timeline of births, deaths, marriages, and residences" },
    { href: "/pedigree", label: "Pedigree Chart", color: "var(--accent-orange)", desc: "Ancestor tree for any individual in the database" },
  ]

  return (
    <div className="p-8 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold mb-2">Roots Graph</h1>
      <p className="text-sm mb-8" style={{ color: "#888" }}>
        Local-first genealogy data cleanup and research workspace
      </p>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {statCards.map((c) => (
          <div
            key={c.label}
            className="rounded-xl p-5 border"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            <div className="text-3xl font-bold" style={{ color: c.color }}>{c.value}</div>
            <div className="text-sm mt-1" style={{ color: "#888" }}>{c.label}</div>
          </div>
        ))}
      </div>

      {/* Notable */}
      {stats?.oldest_individual && stats?.most_recent_individual && (
        <div className="grid grid-cols-2 gap-4 mb-8">
          <div
            className="rounded-xl p-4 border"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            <div className="text-xs mb-1" style={{ color: "#888" }}>Earliest Ancestor</div>
            <div className="text-sm font-semibold" style={{ color: "var(--accent)" }}>
              {stats.oldest_individual.name}
            </div>
            <div className="text-xs" style={{ color: "#666" }}>
              Born {stats.oldest_individual.year}
            </div>
          </div>
          <div
            className="rounded-xl p-4 border"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            <div className="text-xs mb-1" style={{ color: "#888" }}>Most Recent</div>
            <div className="text-sm font-semibold" style={{ color: "var(--accent-pink)" }}>
              {stats.most_recent_individual.name}
            </div>
            <div className="text-xs" style={{ color: "#666" }}>
              Born {stats.most_recent_individual.year}
            </div>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <div
          className="rounded-xl p-4 border"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h3 className="text-sm font-semibold mb-3" style={{ color: "#888" }}>
            Surname Distribution
          </h3>
          <svg ref={barRef} className="w-full" style={{ height: 200 }} />
        </div>
        <div
          className="rounded-xl p-4 border"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <h3 className="text-sm font-semibold mb-3" style={{ color: "#888" }}>
            Births by Decade
          </h3>
          <svg ref={histRef} className="w-full" style={{ height: 200 }} />
        </div>
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-2 gap-4">
        {features.map((f) => (
          <a
            key={f.href}
            href={f.href}
            className="rounded-xl p-6 border transition-colors"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            <h2 className="text-lg font-semibold mb-2" style={{ color: f.color }}>
              {f.label}
            </h2>
            <p className="text-sm" style={{ color: "#888" }}>{f.desc}</p>
          </a>
        ))}
      </div>
    </div>
  )
}
