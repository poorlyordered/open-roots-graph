"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import type { MigrationEvent, FamilyLine } from "@/lib/types"
import L from "leaflet"

interface Props {
  events: MigrationEvent[]
  familyLines: FamilyLine[]
  decade: number
  activeSurnames: Set<string>
}

const FAMILY_COLORS: Record<string, string> = {}

function getColor(surname: string, familyLines: FamilyLine[]): string {
  if (!FAMILY_COLORS[surname]) {
    const line = familyLines.find((l) => l.surname === surname)
    FAMILY_COLORS[surname] = line?.color || "#888888"
  }
  return FAMILY_COLORS[surname]
}

export default function MigrationMap({ events, familyLines, decade, activeSurnames }: Props) {
  const mapRef = useRef<L.Map | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const markersRef = useRef<L.LayerGroup | null>(null)
  const arcsRef = useRef<L.LayerGroup | null>(null)

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = L.map(containerRef.current, {
      center: [38.5, -82],
      zoom: 6,
      zoomControl: true,
    })

    // Dark tile layer
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 19,
      }
    ).addTo(map)

    markersRef.current = L.layerGroup().addTo(map)
    arcsRef.current = L.layerGroup().addTo(map)
    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Update markers and arcs when decade or filters change
  const updateMap = useCallback(() => {
    if (!markersRef.current || !arcsRef.current) return

    markersRef.current.clearLayers()
    arcsRef.current.clearLayers()

    // Filter events by decade and active surnames
    const visibleEvents = events.filter((e) => {
      if (e.surname && !activeSurnames.has(e.surname)) return false
      const born = e.birth_year || 0
      const died = e.death_year || 9999
      // Show if person was alive during this decade
      return born <= decade + 10 && died >= decade - 10
    })

    // Aggregate points by location
    const locationCounts: Record<string, { lat: number; lng: number; count: number; names: string[] }> = {}

    for (const event of visibleEvents) {
      for (const pt of event.points) {
        if (pt.year && pt.year > decade + 10) continue
        const key = `${pt.lat.toFixed(4)},${pt.lng.toFixed(4)}`
        if (!locationCounts[key]) {
          locationCounts[key] = { lat: pt.lat, lng: pt.lng, count: 0, names: [] }
        }
        locationCounts[key].count++
        if (locationCounts[key].names.length < 5) {
          locationCounts[key].names.push(event.name)
        }
      }
    }

    // Draw location markers
    for (const loc of Object.values(locationCounts)) {
      const radius = Math.min(4 + Math.sqrt(loc.count) * 3, 20)
      const marker = L.circleMarker([loc.lat, loc.lng], {
        radius,
        fillColor: "#4488ff",
        fillOpacity: 0.6,
        color: "#6699ff",
        weight: 1,
      })
      marker.bindPopup(
        `<div style="font-size:13px"><strong>${loc.count} individual${loc.count > 1 ? "s" : ""}</strong><br/>` +
          loc.names.join("<br/>") +
          (loc.count > 5 ? `<br/><em>...and ${loc.count - 5} more</em>` : "") +
          "</div>"
      )
      markersRef.current!.addLayer(marker)
    }

    // Draw migration arcs (parent birthplace -> child birthplace)
    for (const event of visibleEvents) {
      const pts = event.points.filter((p) => !p.year || p.year <= decade + 10)
      if (pts.length < 2) continue

      const color = getColor(event.surname || "Unknown", familyLines)

      for (let i = 0; i < pts.length - 1; i++) {
        const from = pts[i]
        const to = pts[i + 1]

        // Skip if same location
        if (Math.abs(from.lat - to.lat) < 0.01 && Math.abs(from.lng - to.lng) < 0.01) continue

        // Curved line using a midpoint offset
        const midLat = (from.lat + to.lat) / 2
        const midLng = (from.lng + to.lng) / 2
        const dx = to.lng - from.lng
        const dy = to.lat - from.lat
        const offset = Math.sqrt(dx * dx + dy * dy) * 0.15
        const curveLat = midLat + offset * 0.5
        const curveLng = midLng - offset * 0.3

        const line = L.polyline(
          [
            [from.lat, from.lng],
            [curveLat, curveLng],
            [to.lat, to.lng],
          ],
          {
            color,
            weight: 1.5,
            opacity: 0.5,
            dashArray: "4 4",
          }
        )

        line.bindPopup(
          `<div style="font-size:13px"><strong>${event.name}</strong><br/>` +
            `${from.place} &rarr; ${to.place}</div>`
        )

        arcsRef.current!.addLayer(line)
      }
    }
  }, [events, familyLines, decade, activeSurnames])

  useEffect(() => {
    updateMap()
  }, [updateMap])

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ minHeight: "500px" }}
    />
  )
}
