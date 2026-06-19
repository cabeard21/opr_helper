export type ApiEnvelope<T> = {
  data: T | null
  error: string | Record<string, unknown> | null
}

export type Faction = {
  id: number
  name: string
  version: string
  last_fetched: string | null
  source_uid: string | null
  unit_count: number
}

export type Weapon = {
  id: number
  name: string
  range: number
  attacks: number
  attacks_string: string
  ap: number
  special_rules: Record<string, unknown>
  source_uid: string | null
}

export type UnitWeaponSlot = {
  id: number
  weapon: Weapon
  is_default: boolean
  upgrade_cost: number
}

export type Unit = {
  id: number
  faction: number
  name: string
  quality: number
  defense: number
  tough: number
  points: number
  min_models: number
  max_models: number | null
  default_models: number
  special_rules: Record<string, unknown>
  source_uid: string | null
  weapon_slots: UnitWeaponSlot[]
}

export type ListValidationMessage = {
  code: string
  message: string
  list_unit_id?: number
}

export type ListValidation = {
  errors: ListValidationMessage[]
  warnings: ListValidationMessage[]
}

export type ListUnit = {
  id: number
  unit: number
  unit_name: string
  unit_points: number
  model_count: number
  selected_weapon_slot: number | null
  selected_weapon_name: string | null
  notes: string
  total_points: number
}

export type ArmyList = {
  id: number
  name: string
  faction: number
  point_limit: number
  created_at: string
  updated_at: string
  units: ListUnit[]
  total_points: number
  validation: ListValidation
}

export type CreateListInput = {
  name: string
  faction: number
  point_limit: number
}

export type AddListUnitInput = {
  unit: number
  model_count: number
  selected_weapon_slot?: number | null
  notes?: string
}

export type UpdateListUnitInput = Partial<{
  model_count: number
  selected_weapon_slot: number | null
  notes: string
}>

export type AdvisorSuggestionInput = {
  faction: number
  point_limit: number
  prompt: string
  dry_run: boolean
}

export type SuggestedUnit = {
  unit_id: number
  unit_name: string
  model_count: number
  justification: string
}

export type ListSuggestion = {
  units: SuggestedUnit[]
  total_points: number
  archetype: string
  playstyle: string
  activation_count: number
  strategy_summary: string
  warnings: string[]
}

export type AdvisorSuggestionResponse = {
  suggestion: ListSuggestion
  computed_total_points: number
  point_delta: number
  reconciliation_warnings: string[]
  army_list: ArmyList | null
}

export type CalcInput = {
  unit_id: number
  weapon_id: number
  target: {
    defense: number
    tough: number
  }
  modifiers?: {
    stealth?: boolean
    indirect?: boolean
  }
}

export type DistributionPoint = {
  wounds: number
  probability: number
}

export type CalcResult = {
  ev: number
  distribution: DistributionPoint[]
  p_zero_wounds: number
  p_kill_model: number
  p_kill_unit: number
}

export type TargetProfile = {
  id: string
  name: string
  defense: number
  tough: number
}

export type UnitTargetResult = {
  target_id: string
  ev: number
  wounds_per_100_points: number
  p_kill_model: number
}

export type ListAnalysisUnit = {
  list_unit_id: number
  unit_id: number
  unit_name: string
  model_count: number
  points: number
  weapon_id: number
  weapon_name: string
  target_results: UnitTargetResult[]
}

export type ListAnalysisTotal = {
  target_id: string
  ev: number
  wounds_per_100_points: number
}

export type ListAnalysisResult = {
  list_id: number
  targets: TargetProfile[]
  units: ListAnalysisUnit[]
  totals: ListAnalysisTotal[]
}
