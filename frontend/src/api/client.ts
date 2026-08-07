import { clearStoredAccessToken, getStoredAccessToken } from './authToken'
import type { ProblemDetail } from '../types/api'

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1'

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined
  return configured && configured.length > 0 ? configured : DEFAULT_BASE_URL
}

export class ApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function authorizationHeaders(): Record<string, string> {
  const token = getStoredAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function parseErrorAndThrow(response: Response): Promise<never> {
  if (response.status === 401 && getStoredAccessToken()) {
    clearStoredAccessToken()
    window.dispatchEvent(new CustomEvent('exam-quality:auth-expired'))
  }
  let detail = response.statusText || `Request failed with status ${response.status}`
  try {
    const problem = (await response.json()) as Partial<ProblemDetail>
    if (problem.detail) detail = problem.detail
  } catch {
    // Response body wasn't JSON - fall back to statusText.
  }
  throw new ApiError(response.status, detail)
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: { ...authorizationHeaders() },
    signal,
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authorizationHeaders() },
    body: JSON.stringify(body),
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}

export async function apiPutJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authorizationHeaders() },
    body: JSON.stringify(body),
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers: { ...authorizationHeaders() },
    body: form,
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}

/** Protected report downloads require the same bearer token as every other API request. */
export async function apiGetBlob(path: string): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: { ...authorizationHeaders() },
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return response.blob()
}

export interface ApiBlobResponse {
  blob: Blob
  headers: Headers
}

export async function apiGetBlobResponse(path: string): Promise<ApiBlobResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: { ...authorizationHeaders() },
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return { blob: await response.blob(), headers: response.headers }
}

export async function apiPostNoContent(path: string, body: unknown = {}): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authorizationHeaders() },
    body: JSON.stringify(body),
  })
  if (!response.ok) return parseErrorAndThrow(response)
}

export async function apiDeleteNoContent(path: string): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'DELETE',
    headers: { ...authorizationHeaders() },
  })
  if (!response.ok) return parseErrorAndThrow(response)
}

export async function apiPatchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authorizationHeaders() },
    body: JSON.stringify(body),
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}
