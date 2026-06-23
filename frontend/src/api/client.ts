import axios from 'axios'

import type {
  AddListUnitInput,
  AdvisorSuggestionInput,
  AdvisorSuggestionResponse,
  ApiEnvelope,
  ArmyForgeExport,
  ArmyList,
  CalcInput,
  CalcResult,
  CreateListInput,
  Faction,
  ListAnalysisResult,
  TargetProfile,
  Unit,
  UpdateListUnitInput,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

function http() {
  return axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

function formatError(error: ApiEnvelope<unknown>['error']): string {
  if (!error) {
    return 'Request failed.'
  }
  if (typeof error === 'string') {
    return error
  }
  return JSON.stringify(error)
}

function unwrap<T>(envelope: ApiEnvelope<T>): T {
  if (envelope.error || envelope.data === null) {
    throw new Error(formatError(envelope.error))
  }
  return envelope.data
}

function unwrapHttpError(error: unknown): never {
  if (axios.isAxiosError<ApiEnvelope<unknown>>(error) && error.response?.data) {
    unwrap(error.response.data)
  }
  throw error
}

async function getEnvelope<T>(path: string): Promise<T> {
  try {
    const response = await http().get<ApiEnvelope<T>>(path)
    return unwrap(response.data)
  } catch (error) {
    unwrapHttpError(error)
  }
}

async function postEnvelope<T, TBody>(path: string, body: TBody): Promise<T> {
  try {
    const response = await http().post<ApiEnvelope<T>>(path, body)
    return unwrap(response.data)
  } catch (error) {
    unwrapHttpError(error)
  }
}

async function patchEnvelope<T, TBody>(path: string, body: TBody): Promise<T> {
  try {
    const response = await http().patch<ApiEnvelope<T>>(path, body)
    return unwrap(response.data)
  } catch (error) {
    unwrapHttpError(error)
  }
}

async function deleteEnvelope<T>(path: string): Promise<T> {
  try {
    const response = await http().delete<ApiEnvelope<T>>(path)
    return unwrap(response.data)
  } catch (error) {
    unwrapHttpError(error)
  }
}

export const apiClient = {
  getFactions: () => getEnvelope<Faction[]>('/factions/'),
  getFactionUnits: (factionId: number) => getEnvelope<Unit[]>(`/factions/${factionId}/units/`),
  getUnit: (unitId: number) => getEnvelope<Unit>(`/units/${unitId}/`),
  getLists: () => getEnvelope<ArmyList[]>('/lists/'),
  createList: (input: CreateListInput) => postEnvelope<ArmyList, CreateListInput>('/lists/', input),
  getList: (listId: number) => getEnvelope<ArmyList>(`/lists/${listId}/`),
  updateList: (listId: number, input: Partial<CreateListInput>) =>
    patchEnvelope<ArmyList, Partial<CreateListInput>>(`/lists/${listId}/`, input),
  deleteList: (listId: number) => deleteEnvelope<{ deleted: boolean }>(`/lists/${listId}/`),
  addListUnit: (listId: number, input: AddListUnitInput) =>
    postEnvelope<ArmyList, AddListUnitInput>(`/lists/${listId}/units/`, input),
  updateListUnit: (listId: number, listUnitId: number, input: UpdateListUnitInput) =>
    patchEnvelope<ArmyList, UpdateListUnitInput>(`/lists/${listId}/units/${listUnitId}/`, input),
  removeListUnit: (listId: number, listUnitId: number) =>
    deleteEnvelope<ArmyList>(`/lists/${listId}/units/${listUnitId}/`),
  calculateEv: (input: CalcInput) => postEnvelope<CalcResult, CalcInput>('/calc/ev/', input),
  analyzeList: (listId: number, targets: TargetProfile[]) =>
    postEnvelope<ListAnalysisResult, { targets: TargetProfile[] }>(`/lists/${listId}/analysis/`, { targets }),
  exportArmyForgeList: (listId: number) => getEnvelope<ArmyForgeExport>(`/lists/${listId}/export/army-forge/`),
  suggestArmyList: (input: AdvisorSuggestionInput) =>
    postEnvelope<AdvisorSuggestionResponse, AdvisorSuggestionInput>('/advisor/suggest/', input),
}
