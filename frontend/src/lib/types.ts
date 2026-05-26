export interface Individual {
  id: string
  name: string
  given_name?: string
  surname?: string
  sex?: string
  birth_date_raw?: string
  birth_date_iso?: string
  birth_year?: number
  death_date_raw?: string
  death_date_iso?: string
  death_year?: number
}

export interface IndividualDetail extends Individual {
  birth_place?: string
  death_place?: string
  burial_place?: string
  parents: Individual[]
  spouses: Individual[]
  children: Individual[]
  sources: string[]
  residences: { place: string; year?: number; date_raw?: string }[]
}

export interface Place {
  normalized: string
  city?: string
  county?: string
  state?: string
  country?: string
  latitude?: number
  longitude?: number
}

export interface GeoPoint {
  lat: number
  lng: number
  place: string
  year?: number
}

export interface MigrationEvent {
  individual_id: string
  name: string
  surname?: string
  birth_year?: number
  death_year?: number
  sex?: string
  points: GeoPoint[]
}

export interface FamilyLine {
  surname: string
  count: number
  color?: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total: number
    limit: number
    offset: number
  }
}

export interface MigrationResponse {
  success: boolean
  data: MigrationEvent[]
  family_lines: FamilyLine[]
}

export interface GraphNode {
  id: string
  name?: string
  label?: string
  surname?: string
  sex?: string
  birth_year?: number
  death_year?: number
  birth_date?: string
  death_date?: string
  marriage_year?: number
  marriage_place?: string
  type: "individual" | "family"
  group: number
  x?: number
  y?: number
  fx?: number | null
  fy?: number | null
}

export interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: "SPOUSE_IN" | "CHILD_OF"
  role?: string
}

export interface GraphData {
  success: boolean
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
  cypherQuery?: string
  queryResults?: Record<string, unknown>[]
}

export interface StreamChunk {
  type: "text" | "cypher" | "data" | "error" | "done"
  content: string
}

export type ChatMode = "query" | "hypothesis" | "research"

export interface Suggestion {
  mode: ChatMode
  text: string
}

export interface TimelineEvent {
  individual_id: string
  name: string
  surname?: string
  sex?: string
  event_type: "birth" | "death" | "marriage" | "residence"
  year?: number
  date_raw?: string
  place?: string
}

export interface TimelineFilters {
  surnames: string[]
  locations: string[]
  year_min: number
  year_max: number
}

export interface PedigreeNode {
  id: string
  name: string
  surname?: string
  sex?: string
  birth_year?: number
  death_year?: number
  birth_place?: string
  death_place?: string
  generation: number
  children?: PedigreeNode[]
}

export interface ResearchPriorityItem {
  id: string
  name: string
  surname?: string
  sex?: string
  birth_year?: number
  death_year?: number
  generation: number
  relationship: "direct" | "collateral"
  completeness_score: number
  priority_score: number
  missing_fields: string[]
  has_conflicts: boolean
  conflict_count: number
  source_count: number
  is_brick_wall: boolean
  confidence_label: "verified" | "high" | "medium" | "low"
  confidence_value: number
  keystone_score: number
}

export interface ResearchPrioritySummary {
  total_scored: number
  brick_walls: number
  avg_completeness: number
  direct_line_count: number
  collateral_count: number
}

export interface RootCandidate {
  id: string
  name: string
  surname?: string
  birth_year?: number
  descendant_count: number
}

export interface Claim {
  id: string
  claim_type: string
  value: string
  confidence: number
  status: string
  extracted_by: string | null
  record_title: string | null
  individual_id?: string
  individual_name?: string
}

export interface Conflict {
  id: string
  description: string
  field: string
  severity: string
  status: string
  resolution?: string | null
  individuals: { id: string; name: string; birth_year: number | null }[]
}

export interface EvidenceSummary {
  total_claims: number
  total_conflicts: number
  open_conflicts: number
  total_tasks: number
  open_tasks: number
  claims_by_type: Record<string, number>
  conflicts_by_severity: Record<string, number>
  completeness: Record<string, number>
}

export interface ResearchTaskItem {
  id: string
  title: string
  description: string
  priority: string
  status: string
  target_name: string | null
}

export interface QualityScoreItem {
  id: string
  name: string
  surname?: string
  sex?: string
  birth_year?: number
  death_year?: number
  completeness_pct: number
  missing_fields: string[]
  missing_count: number
  source_count: number
  conflict_count: number
  priority_score: number
  is_brick_wall: boolean
}

export interface QualitySummary {
  total_individuals: number
  avg_completeness: number
  fully_complete: number
  unsourced_count: number
  quick_win_count: number
  completeness_by_field: Record<string, number>
}

export interface DashboardStats {
  individuals_count: number
  families_count: number
  places_count: number
  geocoded_count: number
  surname_distribution: { surname: string; count: number }[]
  birth_decade_histogram: { decade: number; count: number }[]
  death_decade_histogram: { decade: number; count: number }[]
  oldest_individual: { name: string; year: number } | null
  most_recent_individual: { name: string; year: number } | null
}
