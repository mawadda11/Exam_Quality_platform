import { useOutletContext } from 'react-router-dom'
import type { AnalysisResponse, ProcessingStage } from '../types/api'

export interface AnalysisRouteContext {
  analysis: AnalysisResponse
  refreshAnalysis: () => Promise<AnalysisResponse>
  replaceAnalysis: (analysis: AnalysisResponse) => void
  updateAnalysisState: (state: ProcessingStage) => void
}

export function useAnalysisRoute(): AnalysisRouteContext {
  return useOutletContext<AnalysisRouteContext>()
}
