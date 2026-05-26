"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { getDashboardStats } from "@/lib/api"

const navItems = [
  { href: "/", label: "Dashboard", icon: "◉" },
  { href: "/migration", label: "Migration Map", icon: "◎" },
  { href: "/graph", label: "Network Graph", icon: "◇" },
  { href: "/timeline", label: "Timeline", icon: "▥" },
  { href: "/pedigree", label: "Pedigree", icon: "△" },
  { href: "/individuals", label: "Individuals", icon: "◈" },
  { href: "/evidence", label: "Evidence Board", icon: "◆" },
  { href: "/quality", label: "Data Quality", icon: "◇" },
  { href: "/research-priorities", label: "Research Priorities", icon: "▲" },
  { href: "/assistant", label: "Research Assistant", icon: "▣" },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [stats, setStats] = useState<{ individuals: number; families: number } | null>(null)

  useEffect(() => {
    getDashboardStats()
      .then((d) => {
        if (d.data) {
          setStats({
            individuals: d.data.individuals_count,
            families: d.data.families_count,
          })
        }
      })
      .catch(() => {})
  }, [])

  return (
    <aside className="w-56 flex-shrink-0 flex flex-col border-r"
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
        <h1 className="text-lg font-bold" style={{ color: "var(--accent)" }}>
          Roots Graph
        </h1>
        <p className="text-xs mt-1" style={{ color: "#666" }}>
          Local genealogy workspace
        </p>
      </div>
      <nav className="flex-1 p-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors mb-0.5"
              style={{
                background: isActive ? "var(--surface-hover)" : "transparent",
                color: isActive ? "var(--accent)" : "var(--foreground)",
              }}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>
      <div className="p-4 text-xs" style={{ color: "#444" }}>
        {stats
          ? `${stats.individuals} individuals \u00B7 ${stats.families} families`
          : "\u00A0"}
      </div>
    </aside>
  )
}
