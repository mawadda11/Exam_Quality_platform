import { useEffect, useState } from 'react'
import { listReportLibrary } from '../../api/reports'

export type ReportsAvailableState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; count: number }

/** Dashboard-only count of reports with an up-to-date, downloadable PDF.
 * `page_size: 1` keeps this to one lightweight request - only the
 * authoritative `total` from the paginated envelope is used, never the
 * (single) returned item. Kept independent from useAnalyses so a failure
 * here never blocks the rest of the dashboard. */
export function useReportsAvailableCount(): ReportsAvailableState {
  const [state, setState] = useState<ReportsAvailableState>({ status: 'loading' })

  useEffect(() => {
    let active = true
    listReportLibrary({ status: 'available', page: 1, page_size: 1 })
      .then((page) => {
        if (active) setState({ status: 'ready', count: page.total })
      })
      .catch(() => {
        if (active) setState({ status: 'error' })
      })
    return () => {
      active = false
    }
  }, [])

  return state
}
