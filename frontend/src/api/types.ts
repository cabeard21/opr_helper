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
  count?: number | null
  upgrade_cost: number
  option_id: string | null
  upgrade_id: string | null
}

export type UnitUpgradeOption = {
  id: number
  option_uid: string
  label: string
  cost: number
  gains: Record<string, unknown>[]
  weapons: Weapon[]
}

export type UnitUpgradeSection = {
  id: number
  package_uid: string
  section_uid: string
  label: string
  variant: string
  targets: string[]
  affects?: Record<string, unknown>
  options: UnitUpgradeOption[]
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
  max_models: number
  default_models: number
  special_rules: Record<string, unknown>
  source_uid: string | null
  weapon_slots: UnitWeaponSlot[]
  upgrade_sections: UnitUpgradeSection[]
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
  selected_upgrades: number[]
  selected_upgrade_selections?: Array<{ option: number; quantity: number }>
  loadout_weapon_names: string[]
  loadout_summary: string
  parent_entry: number | null
  combined_from_count: number
  notes: string
  total_points: number
}

export type ArmyList = {
  id: number
  name: string
  faction: number
  point_limit: number
  advisor_archetype: string
  advisor_playstyle: string
  advisor_strategy_summary: string
  advisor_prompt: string
  advisor_warnings: string[]
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
  selected_upgrades?: number[]
  selected_upgrade_selections?: Array<{ option: number; quantity: number }>
  notes?: string
}

export type UpdateListUnitInput = Partial<{
  model_count: number
  selected_weapon_slot: number | null
  selected_upgrades: number[]
  selected_upgrade_selections: Array<{ option: number; quantity: number }>
  parent_entry: number | null
  combined_from_count: number
  notes: string
}>

export type ArmyForgeExport = {
  id: string
  list: {
    id: string
    key: string
    name: string
    units: Array<{
      id: string
      xp: number
      notes: string | null
      armyId: string
      traits: unknown[]
      combined: boolean
      joinToUnit: string | null
      selectionId: string
      selectedUpgrades: Array<{
        optionId: string
        upgradeId: string
        instanceId: string
      }>
    }>
    isCloud: boolean
    forceOrg: boolean
    modified: string
    gameSystem: string
    modelCount: number
    simpleMode: boolean
    description: string
    pointsLimit: number
    campaignMode: boolean
    cloudModified: string
    narrativeMode: boolean
    activationCount: number
  }
  armyId: string
  armyIds: string[]
  armyName: string
  modified: string
  favourite: boolean
  gameSystem: string
  listPoints: number
  armyFaction: string | null
  saveVersion: number
  armyVersions: Array<{ armyId: string; version: string }>
}

export type AdvisorSuggestionInput = {
  faction: number
  point_limit: number
  prompt: string
  dry_run: boolean
  suggestion?: ListSuggestion
}

export type SuggestedUnit = {
  unit_id: number
  unit_name: string
  model_count: number
  combined_from_count: number
  selected_upgrade_ids: number[]
  selected_upgrade_selections?: Array<{ option: number; quantity: number }>
  parent_unit_index?: number | null
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
    unit_size?: number
  }
  modifiers?: {
    stealth?: boolean
    indirect?: boolean
  }
  combat_context?: {
    charging?: boolean
    target_over_9?: boolean
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
  unit_size?: number
  special_rules?: Record<string, unknown>
}

export type UnitTargetResult = {
  target_id: string
  ev: number
  ranged_ev: number
  melee_ev: number
  activation_ev?: number
  burst_ev?: number
  burst_ranged_ev?: number
  burst_melee_ev?: number
  burst_activation_ev?: number
  wounds_per_100_points: number
  ranged_wounds_per_100_points: number
  melee_wounds_per_100_points: number
  activation_wounds_per_100_points?: number
  p_kill_model: number
}

export type ListAnalysisUnit = {
  list_unit_id: number
  unit_id: number
  unit_name: string
  model_count: number
  points: number
  effective_wounds: number
  effective_wounds_per_100_points: number
  weapon_id: number
  weapon_name: string
  weapon_names?: string[]
  limited_weapon_names?: string[]
  target_results: UnitTargetResult[]
}

export type ListAnalysisTotal = {
  target_id: string
  ev: number
  ranged_ev: number
  melee_ev: number
  activation_ev?: number
  burst_ev?: number
  burst_ranged_ev?: number
  burst_melee_ev?: number
  burst_activation_ev?: number
  wounds_per_100_points: number
  ranged_wounds_per_100_points: number
  melee_wounds_per_100_points: number
  activation_wounds_per_100_points?: number
}

export type ListAnalysisResult = {
  list_id: number
  targets: TargetProfile[]
  units: ListAnalysisUnit[]
  totals: ListAnalysisTotal[]
}
