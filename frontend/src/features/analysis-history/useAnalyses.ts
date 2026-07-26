import { useEffect, useState } from 'react'
import { listAnalyses } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse } from '../../types/api'

export type AnalysesLoadState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; analyses: AnalysisResponse[] }

let pendingRequest: Promise<AnalysisResponse[]> | null = null

function loadAnalysesOnce(): Promise<AnalysisResponse[]> {
  if (pendingRequest) return pendingRequest

  const request = listAnalyses()
  pendingRequest = request
  void request.then(
    () => {
      if (pendingRequest === request) pendingRequest = null
    },
    () => {
      if (pendingRequest === request) pendingRequest = null
    },
  )
  return request
}

export function useAnalyses(): AnalysesLoadState {
  const [state, setState] = useState<AnalysesLoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    loadAnalysesOnce()
      .then((analyses) => {
        if (!cancelled) setState({ status: 'ready', analyses })
      })
      .catch((error: unknown) => {
        if (cancelled) return
        setState({
          status: 'error',
          message: error instanceof ApiError ? error.detail : 'Could not load analyses.',
        })
      })
    return () => {
      cancelled = true
    }
  }, [])

  return state
}
