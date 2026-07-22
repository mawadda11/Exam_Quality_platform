import { getStoredDevUserEmail } from './identity'
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

function identityHeaders(): Record<string, string> {
  const email = getStoredDevUserEmail()
  return email ? { 'X-Dev-User-Email': email } : {}
}

async function parseErrorAndThrow(response: Response): Promise<never> {
  let detail = response.statusText || `Request failed with status ${response.status}`
  try {
    const problem = (await response.json()) as Partial<ProblemDetail>
    if (problem.detail) detail = problem.detail
  } catch {
    // Response body wasn't JSON - fall back to statusText.
  }
  throw new ApiError(response.status, detail)
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: { ...identityHeaders() },
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}

export async function apiPostJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...identityHeaders() },
    body: JSON.stringify(body),
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}

export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: 'POST',
    headers: { ...identityHeaders() },
    body: form,
  })
  if (!response.ok) return parseErrorAndThrow(response)
  return (await response.json()) as T
}
