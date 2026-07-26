import type { AnalysisResponse, ProcessingStage } from '../types/api'

const ACTIVE_PROCESSING_STAGES: ReadonlySet<ProcessingStage> = new Set([
  'validating',
  'extracting_exam',
  'extracting_tp153',
  'building_evidence',
  'retrieving_knowledge',
  'applying_rules',
  'generating_report',
])

export function isActiveProcessingState(state: ProcessingStage): boolean {
  return ACTIVE_PROCESSING_STAGES.has(state)
}

export function routeForAnalysis(analysis: AnalysisResponse): string {
  const base = `/analyses/${analysis.id}`
  if (analysis.state === 'completed') return `${base}/results/overview`
  if (analysis.state === 'failed' || isActiveProcessingState(analysis.state)) {
    return `${base}/progress`
  }
  return analysis.ready_for_analysis ? `${base}/start` : `${base}/documents`
}
