import type { AcademicStatus, FindingResponse } from '../../types/api'

export interface FindingFilterValues {
  status: AcademicStatus | 'all'
  dimension: string
  question: string
}

export const EMPTY_FINDING_FILTERS: FindingFilterValues = {
  status: 'all',
  dimension: 'all',
  question: 'all',
}

export function filterFindings(
  findings: FindingResponse[],
  filters: FindingFilterValues,
): FindingResponse[] {
  return findings.filter((finding) => {
    if (filters.status !== 'all' && finding.status !== filters.status) return false
    if (filters.dimension !== 'all' && finding.dimension !== filters.dimension) return false
    if (
      filters.question !== 'all' &&
      !finding.evidence.some(
        (item) =>
          item.evidence_type === 'question_text' &&
          item.item_reference === filters.question,
      )
    ) {
      return false
    }
    return true
  })
}
