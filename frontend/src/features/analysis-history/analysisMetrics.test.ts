import { describe, expect, it } from 'vitest'
import type { AnalysisResponse, ProcessingStage } from '../../types/api'
import { RECENT_ANALYSES_LIMIT, calculateAnalysisMetrics } from './analysisMetrics'

function analysis(
  id: string,
  state: ProcessingStage,
  predecessorAnalysisId: string | null = null,
): AnalysisResponse {
  return {
    id,
    course: {
      id: `course-${id}`,
      code: `CODE-${id}`,
      name: `Course ${id}`,
      department: null,
      program: null,
    },
    exam_type: 'Midterm',
    term: '2026 Spring',
    state,
    owner_user_id: 'user-1',
    predecessor_analysis_id: predecessorAnalysisId,
    uploaded_files: [],
    exam_uploaded: state !== 'queued',
    tp153_uploaded: state !== 'queued',
    ready_for_analysis: state !== 'queued',
    created_at: '2026-07-24T00:00:00Z',
    updated_at: '2026-07-24T00:00:00Z',
  }
}

describe('calculateAnalysisMetrics', () => {
  it('calculates only the three approved dashboard metrics', () => {
    const metrics = calculateAnalysisMetrics([
      analysis('1', 'completed'),
      analysis('2', 'failed', '1'),
      analysis('3', 'validating'),
      analysis('4', 'completed', '2'),
    ])

    expect(metrics.total).toBe(4)
    expect(metrics.completed).toBe(2)
    expect(metrics.linkedReanalyses).toBe(2)
  })

  it('uses the first five backend-ordered records as recent analyses', () => {
    const analyses = Array.from({ length: 7 }, (_, index) =>
      analysis(String(index + 1), 'queued'),
    )

    const metrics = calculateAnalysisMetrics(analyses)

    expect(metrics.recent).toHaveLength(RECENT_ANALYSES_LIMIT)
    expect(metrics.recent.map((item) => item.id)).toEqual(['1', '2', '3', '4', '5'])
  })
})
