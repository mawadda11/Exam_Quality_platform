import { useCallback, useEffect, useRef, useState } from 'react'
import { listAnalyses } from '../../api/analyses'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
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

export type AnalysesLoadResult = AnalysesLoadState & {
  retry: () => void
  removeAnalysis: (analysisId: string) => void
}

export function useAnalyses(): AnalysesLoadResult {
  const { locale, t } = useI18n()
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
            message: localizeInterfaceError(error, locale, t, 'Could not load analyses'),
          })
        }
      })
  }, [locale, t])

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

  const removeAnalysis = useCallback((analysisId: string): void => {
    setState((current) =>
      current.status === 'ready'
        ? {
            status: 'ready',
            analyses: current.analyses.filter((analysis) => analysis.id !== analysisId),
          }
        : current,
    )
  }, [])

  return { ...state, retry, removeAnalysis }
}
