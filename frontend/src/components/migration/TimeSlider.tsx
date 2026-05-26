"use client"

import { useEffect, useRef, useState } from "react"

interface Props {
  decade: number
  onChange: (decade: number) => void
  minYear?: number
  maxYear?: number
}

export default function TimeSlider({ decade, onChange, minYear = 1500, maxYear = 2030 }: Props) {
  const [playing, setPlaying] = useState(false)
  const [internalDecade, setInternalDecade] = useState(decade)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (playing) {
      intervalRef.current = setInterval(() => {
        setInternalDecade((prev) => {
          const next = prev + 10
          if (next > maxYear) {
            setPlaying(false)
            onChange(minYear)
            return minYear
          }
          onChange(next)
          return next
        })
      }, 2000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [playing, maxYear, minYear, onChange])

  // Generate decade marks
  const decades = []
  for (let y = minYear; y <= maxYear; y += 50) {
    decades.push(y)
  }

  return (
    <div
      className="flex items-center gap-4 px-4 py-3 rounded-xl border"
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      <button
        onClick={() => setPlaying(!playing)}
        className="px-3 py-1.5 rounded-lg text-sm font-medium"
        style={{ background: playing ? "var(--accent-pink)" : "var(--accent)", color: "#fff" }}
      >
        {playing ? "Pause" : "Play"}
      </button>

      <div className="flex-1 relative">
        <input
          type="range"
          min={minYear}
          max={maxYear}
          step={10}
          value={decade}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full accent-[var(--accent)] h-2 rounded-lg cursor-pointer"
          style={{ background: "#1a1a3a" }}
        />
        <div className="flex justify-between mt-1">
          {decades.map((y) => (
            <span key={y} className="text-[10px]" style={{ color: "#555" }}>
              {y}
            </span>
          ))}
        </div>
      </div>

      <div
        className="text-2xl font-bold tabular-nums min-w-[5ch] text-center"
        style={{ color: "var(--accent)" }}
      >
        {decade}s
      </div>
    </div>
  )
}
