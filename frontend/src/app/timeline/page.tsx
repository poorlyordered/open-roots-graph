"use client"

import { useEffect, useRef, useState } from "react"
import * as d3 from "d3"
import type { TimelineEvent, TimelineFilters } from "@/lib/types"
import { getTimelineEvents, getTimelineFilters } from "@/lib/api"

const eventColors: Record<string, string> = {
  birth: "#44cc88",
  death: "#ff6688",
  marriage: "#ffaa44",
  residence: "#4488ff",
}

const eventIcons: Record<string, string> = {
  birth: "★",
  death: "✝",
  marriage: "♥",
  residence: "◆",
}

export default function TimelinePage() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [filters, setFilters] = useState<TimelineFilters | null>(null)
  const [surname, setSurname] = useState("")
  const [location, setLocation] = useState("")
  const [yearRange, setYearRange] = useState<[number, number]>([1500, 2030])
  const [activeTypes, setActiveTypes] = useState(["birth", "death", "marriage", "residence"])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  // Load filters on mount
  useEffect(() => {
    getTimelineFilters().then((res) => {
      const f = res.data
      setFilters(f)
      setYearRange([f.year_min, f.year_max])
    })
  }, [])

  // Load events when filters change
  useEffect(() => {
    setLoading(true)
    getTimelineEvents({
      surname: surname || undefined,
      location: location || undefined,
      year_start: yearRange[0],
      year_end: yearRange[1],
      event_types: activeTypes.join(","),
      limit: 1000,
    }).then((res) => {
      setEvents(res.data || [])
      setTotal(res.meta?.total || 0)
      setLoading(false)
    })
  }, [surname, location, yearRange, activeTypes])

  // D3 rendering
  useEffect(() => {
    if (!svgRef.current || events.length === 0) return
    renderTimeline(events)
  }, [events])

  function renderTimeline(data: TimelineEvent[]) {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    svg.selectAll("*").remove()

    const width = svgRef.current.clientWidth
    const margin = { top: 40, right: 40, bottom: 40, left: 40 }
    const centerX = width / 2
    const eventHeight = 32
    const totalHeight = Math.max(data.length * eventHeight + margin.top + margin.bottom, 600)

    svg.attr("height", totalHeight)

    const g = svg.append("g")

    // Zoom
    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.3, 5])
        .on("zoom", (event) => g.attr("transform", event.transform)),
    )

    const years = data.map((d) => d.year!).filter(Boolean)
    const yMin = d3.min(years) || 1500
    const yMax = d3.max(years) || 2030

    const yScale = d3
      .scaleLinear()
      .domain([yMin - 10, yMax + 10])
      .range([margin.top, totalHeight - margin.bottom])

    // Center line
    g.append("line")
      .attr("x1", centerX)
      .attr("y1", margin.top)
      .attr("x2", centerX)
      .attr("y2", totalHeight - margin.bottom)
      .attr("stroke", "#222")
      .attr("stroke-width", 2)

    // Century markers
    const startCentury = Math.floor(yMin / 100) * 100
    const endCentury = Math.ceil(yMax / 100) * 100
    for (let yr = startCentury; yr <= endCentury; yr += 100) {
      const yPos = yScale(yr)
      g.append("line")
        .attr("x1", centerX - 20)
        .attr("y1", yPos)
        .attr("x2", centerX + 20)
        .attr("y2", yPos)
        .attr("stroke", "#333")
        .attr("stroke-width", 1)
      g.append("text")
        .attr("x", centerX)
        .attr("y", yPos - 6)
        .attr("text-anchor", "middle")
        .attr("fill", "#555")
        .attr("font-size", "11px")
        .attr("font-weight", "bold")
        .text(String(yr))
    }

    // Decade markers
    for (let yr = startCentury; yr <= endCentury; yr += 10) {
      if (yr % 100 === 0) continue
      const yPos = yScale(yr)
      g.append("line")
        .attr("x1", centerX - 8)
        .attr("y1", yPos)
        .attr("x2", centerX + 8)
        .attr("y2", yPos)
        .attr("stroke", "#1a1a3a")
        .attr("stroke-width", 1)
    }

    // Events — alternate left/right, offset to avoid overlap
    const sorted = [...data].sort((a, b) => (a.year || 0) - (b.year || 0))

    sorted.forEach((event, i) => {
      const y = yScale(event.year || yMin)
      const side = i % 2 === 0 ? -1 : 1
      const xOffset = 30
      const cardWidth = 220
      const x = centerX + side * xOffset

      const color = eventColors[event.event_type] || "#888"

      // Connector line
      g.append("line")
        .attr("x1", centerX)
        .attr("y1", y)
        .attr("x2", x)
        .attr("y2", y)
        .attr("stroke", color)
        .attr("stroke-width", 1)
        .attr("opacity", 0.4)

      // Circle on center line
      g.append("circle")
        .attr("cx", centerX)
        .attr("cy", y)
        .attr("r", 4)
        .attr("fill", color)

      // Card group
      const cardG = g.append("g").attr("class", "event-card")

      const cardX = side === -1 ? x - cardWidth : x
      cardG
        .append("rect")
        .attr("x", cardX)
        .attr("y", y - 12)
        .attr("width", cardWidth)
        .attr("height", 24)
        .attr("rx", 4)
        .attr("fill", "#0d0d20")
        .attr("stroke", color)
        .attr("stroke-width", 0.5)
        .attr("opacity", 0.9)

      // Event icon
      cardG
        .append("text")
        .attr("x", cardX + 8)
        .attr("y", y + 4)
        .attr("fill", color)
        .attr("font-size", "10px")
        .text(eventIcons[event.event_type] || "●")

      // Name + year
      cardG
        .append("text")
        .attr("x", cardX + 22)
        .attr("y", y + 4)
        .attr("fill", "#ccc")
        .attr("font-size", "11px")
        .text(`${event.name} (${event.year})`)

      // Place
      if (event.place) {
        cardG
          .append("text")
          .attr("x", cardX + cardWidth - 6)
          .attr("y", y + 4)
          .attr("text-anchor", "end")
          .attr("fill", "#555")
          .attr("font-size", "9px")
          .text(event.place.length > 25 ? event.place.slice(0, 25) + "…" : event.place)
      }

      // Hover highlight
      cardG
        .on("mouseenter", () => {
          cardG.select("rect").attr("stroke-width", 1.5).attr("opacity", 1)
          // Highlight same individual
          g.selectAll<SVGGElement, unknown>(".event-card")
            .filter(function () {
              return this !== cardG.node()
            })
            .attr("opacity", 0.3)
        })
        .on("mouseleave", () => {
          cardG.select("rect").attr("stroke-width", 0.5).attr("opacity", 0.9)
          g.selectAll(".event-card").attr("opacity", 1)
        })
    })
  }

  const toggleType = (t: string) => {
    setActiveTypes((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t],
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div
        className="flex items-center gap-4 p-3 border-b flex-shrink-0 flex-wrap"
        style={{ borderColor: "var(--border)", background: "var(--surface)" }}
      >
        <select
          value={surname}
          onChange={(e) => setSurname(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-sm border"
          style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
        >
          <option value="">All surnames</option>
          {filters?.surnames.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <select
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-sm border"
          style={{ background: "#0a0a1a", borderColor: "var(--border)", color: "var(--foreground)" }}
        >
          <option value="">All locations</option>
          {filters?.locations.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>

        {/* Event type toggles */}
        <div className="flex gap-2">
          {Object.entries(eventColors).map(([type, color]) => (
            <button
              key={type}
              onClick={() => toggleType(type)}
              className="text-xs px-2.5 py-1 rounded-lg transition-opacity"
              style={{
                background: activeTypes.includes(type) ? color + "22" : "transparent",
                color: activeTypes.includes(type) ? color : "#444",
                border: `1px solid ${activeTypes.includes(type) ? color + "66" : "#222"}`,
              }}
            >
              {eventIcons[type]} {type}
            </button>
          ))}
        </div>

        <div className="ml-auto text-xs" style={{ color: "#666" }}>
          {loading ? "Loading..." : `${events.length} events (${total} total)`}
        </div>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto">
        {events.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-full">
            <p style={{ color: "#555" }}>No events match the current filters</p>
          </div>
        ) : (
          <svg ref={svgRef} className="w-full" style={{ minHeight: "600px" }} />
        )}
      </div>

      {/* Legend */}
      <div
        className="flex items-center gap-6 px-4 py-2 border-t text-xs"
        style={{ borderColor: "var(--border)", color: "#666" }}
      >
        {Object.entries(eventColors).map(([type, color]) => (
          <span key={type} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ background: color }}
            />
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </span>
        ))}
      </div>
    </div>
  )
}
