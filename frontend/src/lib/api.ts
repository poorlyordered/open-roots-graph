export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export async function getIndividuals(params?: {
  surname?: string
  search?: string
  limit?: number
  offset?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.surname) searchParams.set("surname", params.surname)
  if (params?.search) searchParams.set("search", params.search)
  if (params?.limit) searchParams.set("limit", String(params.limit))
  if (params?.offset) searchParams.set("offset", String(params.offset))
  const qs = searchParams.toString()
  return fetchApi<{ success: boolean; data: import("./types").Individual[]; meta: { total: number } }>(
    `/api/individuals${qs ? `?${qs}` : ""}`
  )
}

export async function getIndividual(id: string) {
  return fetchApi<{ success: boolean; data: import("./types").IndividualDetail }>(
    `/api/individuals/${encodeURIComponent(id)}`
  )
}

export async function getMigrationEvents(params?: {
  surname?: string
  decade_start?: number
  decade_end?: number
}) {
  const searchParams = new URLSearchParams()
  if (params?.surname) searchParams.set("surname", params.surname)
  if (params?.decade_start) searchParams.set("decade_start", String(params.decade_start))
  if (params?.decade_end) searchParams.set("decade_end", String(params.decade_end))
  const qs = searchParams.toString()
  return fetchApi<import("./types").MigrationResponse>(
    `/api/migration/events${qs ? `?${qs}` : ""}`
  )
}

export async function getGraphData() {
  return fetchApi<import("./types").GraphData>("/api/graph")
}

export async function getPlaces(geocodedOnly = false) {
  return fetchApi<{ success: boolean; data: import("./types").Place[] }>(
    `/api/places${geocodedOnly ? "?geocoded_only=true" : ""}`
  )
}

export async function getTimelineEvents(params?: {
  surname?: string
  location?: string
  year_start?: number
  year_end?: number
  event_types?: string
  limit?: number
  offset?: number
}) {
  const sp = new URLSearchParams()
  if (params?.surname) sp.set("surname", params.surname)
  if (params?.location) sp.set("location", params.location)
  if (params?.year_start) sp.set("year_start", String(params.year_start))
  if (params?.year_end) sp.set("year_end", String(params.year_end))
  if (params?.event_types) sp.set("event_types", params.event_types)
  if (params?.limit) sp.set("limit", String(params.limit))
  if (params?.offset) sp.set("offset", String(params.offset))
  const qs = sp.toString()
  return fetchApi<{ success: boolean; data: import("./types").TimelineEvent[]; meta: { total: number } }>(
    `/api/timeline/events${qs ? `?${qs}` : ""}`
  )
}

export async function getTimelineFilters() {
  return fetchApi<{ success: boolean; data: import("./types").TimelineFilters }>(
    "/api/timeline/filters"
  )
}

export async function getPedigree(indiId: string, depth = 5) {
  return fetchApi<{ success: boolean; data: import("./types").PedigreeNode; max_generation: number }>(
    `/api/pedigree/${encodeURIComponent(indiId)}?depth=${depth}`
  )
}

export async function getResearchPriorities(params: {
  root_id: string
  max_generations?: number
  relationship?: string
  limit?: number
  offset?: number
}) {
  const sp = new URLSearchParams()
  sp.set("root_id", params.root_id)
  if (params.max_generations) sp.set("max_generations", String(params.max_generations))
  if (params.relationship) sp.set("relationship", params.relationship)
  if (params.limit) sp.set("limit", String(params.limit))
  if (params.offset) sp.set("offset", String(params.offset))
  return fetchApi<{
    success: boolean
    data: import("./types").ResearchPriorityItem[]
    summary: import("./types").ResearchPrioritySummary
    meta: { total: number; limit: number; offset: number }
  }>(`/api/research-priorities?${sp}`)
}

export async function getRootCandidates() {
  return fetchApi<{ success: boolean; data: import("./types").RootCandidate[] }>(
    "/api/research-priorities/root-candidates"
  )
}

export async function getQualityScores(params?: {
  sort_by?: string
  sort_dir?: string
  limit?: number
  offset?: number
  max_missing?: number
  unsourced_only?: boolean
  missing_field?: string
  search?: string
}) {
  const sp = new URLSearchParams()
  if (params?.sort_by) sp.set("sort_by", params.sort_by)
  if (params?.sort_dir) sp.set("sort_dir", params.sort_dir)
  if (params?.limit) sp.set("limit", String(params.limit))
  if (params?.offset != null) sp.set("offset", String(params.offset))
  if (params?.max_missing != null) sp.set("max_missing", String(params.max_missing))
  if (params?.unsourced_only) sp.set("unsourced_only", "true")
  if (params?.missing_field) sp.set("missing_field", params.missing_field)
  if (params?.search) sp.set("search", params.search)
  const qs = sp.toString()
  return fetchApi<{
    success: boolean
    data: import("./types").QualityScoreItem[]
    summary: import("./types").QualitySummary
    meta: { total: number; limit: number; offset: number }
  }>(`/api/quality/scores${qs ? `?${qs}` : ""}`)
}

export async function getDashboardStats() {
  return fetchApi<{ success: boolean; data: import("./types").DashboardStats }>(
    "/api/stats/dashboard"
  )
}

export async function getSuggestions() {
  return fetchApi<{ success: boolean; data: import("./types").Suggestion[] }>(
    "/api/assistant/suggestions"
  )
}

export async function getEvidenceSummary() {
  return fetchApi<{ success: boolean; data: import("./types").EvidenceSummary }>(
    "/api/evidence/summary"
  )
}

export async function getClaimsForIndividual(indiId: string) {
  return fetchApi<{ success: boolean; data: import("./types").Claim[] }>(
    `/api/evidence/claims/${encodeURIComponent(indiId)}`
  )
}

export async function getConflictsForIndividual(indiId: string) {
  return fetchApi<{ success: boolean; data: import("./types").Conflict[] }>(
    `/api/evidence/conflicts/individual/${encodeURIComponent(indiId)}`
  )
}

export async function getConflicts(params?: { status?: string; severity?: string; limit?: number; offset?: number }) {
  const sp = new URLSearchParams()
  if (params?.status) sp.set("status", params.status)
  if (params?.severity) sp.set("severity", params.severity)
  if (params?.limit) sp.set("limit", String(params.limit))
  if (params?.offset) sp.set("offset", String(params.offset))
  const qs = sp.toString()
  return fetchApi<{ success: boolean; data: import("./types").Conflict[]; meta: { total: number } }>(
    `/api/evidence/conflicts${qs ? `?${qs}` : ""}`
  )
}

export async function getTasks(params?: { status?: string; priority?: string; limit?: number; offset?: number }) {
  const sp = new URLSearchParams()
  if (params?.status) sp.set("status", params.status)
  if (params?.priority) sp.set("priority", params.priority)
  if (params?.limit) sp.set("limit", String(params.limit))
  if (params?.offset) sp.set("offset", String(params.offset))
  const qs = sp.toString()
  return fetchApi<{ success: boolean; data: import("./types").ResearchTaskItem[]; meta: { total: number } }>(
    `/api/evidence/tasks${qs ? `?${qs}` : ""}`
  )
}

export async function patchClaim(claimId: string, body: { status?: string; confidence?: number }) {
  const res = await fetch(`${API_BASE}/api/evidence/claims/${claimId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function patchConflict(conflictId: string, body: { status: string; resolution?: string | null }) {
  const res = await fetch(`${API_BASE}/api/evidence/conflicts/${conflictId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export async function streamChat(
  message: string,
  history: import("./types").ChatMessage[],
  mode: import("./types").ChatMode,
  onChunk: (chunk: import("./types").StreamChunk) => void,
): Promise<AbortController> {
  const controller = new AbortController()
  const res = await fetch(`${API_BASE}/api/assistant/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      history: history.map((m) => ({ role: m.role, content: m.content })),
      mode,
    }),
    signal: controller.signal,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    onChunk({ type: "error", content: err.detail || "Request failed" })
    onChunk({ type: "done", content: "" })
    return controller
  }

  const reader = res.body?.getReader()
  if (!reader) {
    onChunk({ type: "error", content: "No response stream" })
    onChunk({ type: "done", content: "" })
    return controller
  }

  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const lines = buffer.split("\n\n")
    buffer = lines.pop() || ""

    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed.startsWith("data: ")) {
        try {
          const chunk = JSON.parse(trimmed.slice(6))
          onChunk(chunk)
        } catch {
          // skip malformed chunks
        }
      }
    }
  }

  return controller
}
