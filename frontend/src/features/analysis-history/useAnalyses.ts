import { useCallback, useEffect, useRef, useState } from 'react'
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

export type AnalysesLoadResult = AnalysesLoadState & { retry: () => void }

export function useAnalyses(): AnalysesLoadResult {
  const [state, setState] = useState<AnalysesLoadState>({ status: 'loading' })
  const mountedRef = useRef(false)
  const requestTokenRef = useRef(0)

  const load = useCallback((): void => {
    const token = requestTokenRef.current + 1
    requestTokenRef.current = token

    void loadAnalysesOnce()
      .then((analyses) => {
        if (mountedRef.current && requestTokenRef.current === token) {
          setState({ status: 'ready', analyses })
        }
      })
      .catch((error: unknown) => {
        if (mountedRef.current && requestTokenRef.current === token) {
          setState({
            status: 'error',
            message: error instanceof ApiError ? error.detail : 'Could not load analyses.',
          })
        }
      })
  }, [])

  useEffect(() => {
    mountedRef.current = true
    load()
    return () => {
      mountedRef.current = false
    }
  }, [load])

  const retry = useCallback((): void => {
    if (state.status !== 'error') return
    setState({ status: 'loading' })
    load()
  }, [load, state.status])

  return { ...state, retry }
}
