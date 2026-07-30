import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as reportsApi from '../../api/reports'
import { useReportsAvailableCount } from './useReportsAvailableCount'

vi.mock('../../api/reports')

beforeEach(() => {
  vi.mocked(reportsApi.listReportLibrary).mockReset()
})

describe('useReportsAvailableCount', () => {
  it('requests only the available-report total with a minimal page size', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockResolvedValue({
      items: [],
      total: 4,
      page: 1,
      page_size: 1,
      total_pages: 4,
    })

    const { result } = renderHook(() => useReportsAvailableCount())

    expect(result.current).toEqual({ status: 'loading' })
    await waitFor(() => expect(result.current).toEqual({ status: 'ready', count: 4 }))
    expect(reportsApi.listReportLibrary).toHaveBeenCalledWith({
      status: 'available',
      page: 1,
      page_size: 1,
    })
  })

  it('reports an error state without throwing when the request fails', async () => {
    vi.mocked(reportsApi.listReportLibrary).mockRejectedValue(new Error('network error'))

    const { result } = renderHook(() => useReportsAvailableCount())

    await waitFor(() => expect(result.current).toEqual({ status: 'error' }))
  })
})
