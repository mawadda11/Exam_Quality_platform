import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getReportMetadata, listReportLibrary } from './reports'

function mockResponse(body: unknown): Response {
  return {
    ok: true,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('reports API', () => {
  it('requests the bounded report library with encoded filters', async () => {
    const response = {
      items: [],
      total: 0,
      page: 2,
      page_size: 12,
      total_pages: 0,
    }
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(response))
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      listReportLibrary({
        q: 'CPIT 450',
        status: 'available',
        exam_type: 'Final',
        language: 'ar',
        sort: 'oldest',
        page: 2,
        page_size: 12,
      }),
    ).resolves.toEqual(response)

    const requestedUrl = new URL(fetchMock.mock.calls[0][0] as string)
    expect(requestedUrl.pathname).toBe('/api/v1/reports')
    expect(Object.fromEntries(requestedUrl.searchParams)).toEqual({
      q: 'CPIT 450',
      status: 'available',
      exam_type: 'Final',
      language: 'ar',
      sort: 'oldest',
      page: '2',
      page_size: '12',
    })
  })

  it('requests owner-safe report metadata by opaque identifier', async () => {
    const report = { id: 'report-1' }
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(report))
    vi.stubGlobal('fetch', fetchMock)

    await expect(getReportMetadata('report-1')).resolves.toEqual(report)
    expect(fetchMock.mock.calls[0][0]).toBe(
      'http://localhost:8000/api/v1/reports/report-1',
    )
  })
})
