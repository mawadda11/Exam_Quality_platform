import { useId } from 'react'
import { Button } from '../../components/ui/Button'
import type { AcademicStatus, FindingResponse } from '../../types/api'
import {
  EMPTY_FINDING_FILTERS,
  type FindingFilterValues,
} from './findingFilterModel'

const ACADEMIC_STATUSES: AcademicStatus[] = [
  'Satisfied',
  'Partially Satisfied',
  'Not Satisfied',
  'Not Verified',
  'Not Applicable',
]

interface FindingFiltersProps {
  findings: FindingResponse[]
  values: FindingFilterValues
  resultCount: number
  onChange: (values: FindingFilterValues) => void
}

export function FindingFilters({
  findings,
  values,
  resultCount,
  onChange,
}: FindingFiltersProps) {
  const id = useId()
  const dimensions = [...new Set(findings.map((finding) => finding.dimension))].sort()
  const questions = [
    ...new Set(
      findings.flatMap((finding) =>
        finding.evidence
          .filter((item) => item.evidence_type === 'question_text')
          .map((item) => item.item_reference),
      ),
    ),
  ].sort()
  const hasFilters =
    values.status !== 'all' || values.dimension !== 'all' || values.question !== 'all'

  return (
    <div className="finding-filters" aria-label="Filter findings">
      <div className="finding-filter-fields">
        <label htmlFor={`${id}-status`}>
          Status
          <select
            id={`${id}-status`}
            value={values.status}
            onChange={(event) =>
              onChange({
                ...values,
                status: event.target.value as FindingFilterValues['status'],
              })
            }
          >
            <option value="all">All statuses</option>
            {ACADEMIC_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor={`${id}-question`}>
          Question
          <select
            id={`${id}-question`}
            value={values.question}
            onChange={(event) => onChange({ ...values, question: event.target.value })}
          >
            <option value="all">All questions</option>
            {questions.map((question) => (
              <option key={question} value={question}>
                {question}
              </option>
            ))}
          </select>
        </label>
        <label htmlFor={`${id}-dimension`}>
          Dimension
          <select
            id={`${id}-dimension`}
            value={values.dimension}
            onChange={(event) => onChange({ ...values, dimension: event.target.value })}
          >
            <option value="all">All dimensions</option>
            {dimensions.map((dimension) => (
              <option key={dimension} value={dimension}>
                {dimension}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="finding-filter-summary">
        <span role="status">
          Showing {resultCount} of {findings.length} findings
        </span>
        {hasFilters && (
          <Button variant="ghost" onClick={() => onChange(EMPTY_FINDING_FILTERS)}>
            Reset filters
          </Button>
        )}
      </div>
    </div>
  )
}
