"use client"

import { useEffect, useState, useCallback, useMemo } from "react"
import dynamic from "next/dynamic"
import type { MigrationEvent, FamilyLine } from "@/lib/types"
import { getMigrationEvents } from "@/lib/api"
import TimeSlider from "@/components/migration/TimeSlider"
import FamilyLineToggle from "@/components/migration/FamilyLineToggle"

const MigrationMap = dynamic(
  () => import("@/components/migration/MigrationMap"),
  { ssr: false }
)

export default function MigrationPage() {
  const [events, setEvents] = useState<MigrationEvent[]>([])
  const [familyLines, setFamilyLines] = useState<FamilyLine[]>([])
  const [decade, setDecade] = useState(1850)
  const [activeSurnames, setActiveSurnames] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const res = await getMigrationEvents()
        setEvents(res.data)
        setFamilyLines(res.family_lines)
        setActiveSurnames(new Set(res.family_lines.map((l) => l.surname)))
      } catch (err) {
        console.error("Failed to load migration data:", err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleDecadeChange = useCallback((val: number | ((prev: number) => number)) => {
    setDecade(val as number)
  }, [])

  const handleToggle = useCallback((surname: string) => {
    setActiveSurnames((prev) => {
      const next = new Set(prev)
      if (next.has(surname)) {
        next.delete(surname)
      } else {
        next.add(surname)
      }
      return next
    })
  }, [])

  const handleSelectAll = useCallback(() => {
    setActiveSurnames(new Set(familyLines.map((l) => l.surname)))
  }, [familyLines])

  const handleSelectNone = useCallback(() => {
    setActiveSurnames(new Set())
  }, [])

  // Count visible individuals at current decade
  const visibleCount = useMemo(() => {
    return events.filter((e) => {
      if (e.surname && !activeSurnames.has(e.surname)) return false
      const born = e.birth_year || 0
      const died = e.death_year || 9999
      return born <= decade + 10 && died >= decade - 10
    }).length
  }, [events, decade, activeSurnames])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg" style={{ color: "#666" }}>Loading migration data...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Map */}
      <div className="flex-1 relative">
        <MigrationMap
          events={events}
          familyLines={familyLines}
          decade={decade}
          activeSurnames={activeSurnames}
        />

        {/* Overlay: family line toggles */}
        <div className="absolute top-3 right-3 w-52 z-[1000]">
          <FamilyLineToggle
            familyLines={familyLines}
            activeSurnames={activeSurnames}
            onToggle={handleToggle}
            onSelectAll={handleSelectAll}
            onSelectNone={handleSelectNone}
          />
        </div>

        {/* Overlay: visible count */}
        <div
          className="absolute top-3 left-14 z-[1000] px-3 py-2 rounded-lg text-sm"
          style={{ background: "rgba(20,20,40,0.9)", borderColor: "var(--border)", border: "1px solid var(--border)" }}
        >
          <span style={{ color: "var(--accent)" }}>{visibleCount}</span>
          <span style={{ color: "#888" }}> individuals visible</span>
        </div>
      </div>

      {/* Time slider */}
      <div className="p-3">
        <TimeSlider
          decade={decade}
          onChange={handleDecadeChange}
          minYear={1500}
          maxYear={2030}
        />
      </div>
    </div>
  )
}
