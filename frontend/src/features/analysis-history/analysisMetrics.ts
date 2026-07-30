import type { AnalysisResponse } from '../../types/api'

export const RECENT_ANALYSES_LIMIT = 5

export interface AnalysisMetrics {
  total: number
  completed: number
  needsAttention: number
  recent: AnalysisResponse[]
}

export function calculateAnalysisMetrics(analyses: AnalysisResponse[]): AnalysisMetrics {
  return {
    total: analyses.length,
    completed: analyses.filter((analysis) => analysis.state === 'completed').length,
    needsAttention: analyses.filter((analysis) => analysis.state === 'failed').length,
    recent: analyses.slice(0, RECENT_ANALYSES_LIMIT),
  }
}
