import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet, apiPostJson, getApiBaseUrl } from './client'
import { setStoredDevUserEmail } from './identity'

function mockResponse(body: unknown, ok: boolean, status: number, statusText = ''): Response {
  return {
    ok,
    status,
    statusText,
    json: async () => body,
  } as unknown as Response
}

afterEach(() => {
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('getApiBaseUrl', () => {
  it('falls back to the default backend URL when VITE_API_BASE_URL is not set', () => {
    expect(getApiBaseUrl()).toBe('http://localhost:8000/api/v1')
  })
})

describe('apiGet', () => {
  it('attaches the dev identity header when one is stored', async () => {
    setStoredDevUserEmail('prof@kau.edu.sa')
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }, true, 200))
    vi.stubGlobal('fetch', fetchMock)

    await apiGet('/analyses')

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>)['X-Dev-User-Email']).toBe('prof@kau.edu.sa')
  })

  it('omits the identity header when no email is stored', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ ok: true }, true, 200))
    vi.stubGlobal('fetch', fetchMock)

    await apiGet('/analyses')

    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>)['X-Dev-User-Email']).toBeUndefined()
  })

  it('throws an ApiError with the Problem-Details detail message on failure', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      mockResponse(
        { type: 'about:blank', title: 'Not Found', status: 404, detail: 'Analysis not found.' },
        false,
        404,
        'Not Found',
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiGet('/analyses/missing')).rejects.toThrow(ApiError)
    await expect(apiGet('/analyses/missing')).rejects.toMatchObject({
      status: 404,
      detail: 'Analysis not found.',
    })
  })

  it('falls back to statusText when the error body is not JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => {
        throw new Error('not json')
      },
    } as unknown as Response)
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiGet('/analyses')).rejects.toMatchObject({
      status: 500,
      detail: 'Internal Server Error',
    })
  })
})

describe('apiPostJson', () => {
  it('sends a JSON body with the correct method and headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse({ id: '123' }, true, 201))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiPostJson<{ id: string }>('/analyses', { term: '2026 Spring' })

    expect(result).toEqual({ id: '123' })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/api/v1/analyses')
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body as string)).toEqual({ term: '2026 Spring' })
  })
})
