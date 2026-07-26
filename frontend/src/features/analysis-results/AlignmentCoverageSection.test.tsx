import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type {
  AssessmentRecordResponse,
  CloResponse,
  FindingResponse,
  TopicResponse,
} from '../../types/api'
import { AlignmentCoverageSection } from './AlignmentCoverageSection'
import { buildLookups } from './lookups'
import type { ResultResource } from './useAnalysisResultsData'

function ready<T>(data: T): ResultResource<T> {
  return { status: 'ready', data }
}

function finding(overrides: Partial<FindingResponse>): FindingResponse {
  return {
    id: 'finding-1',
    analysis_id: 'analysis-1',
    requirement_id: 'REQ001',
    rule_id: 'RULE001',
    recommendation_id: null,
    status: 'Satisfied',
    explanation: 'Every scorable question cites an explicit CLO reference.',
    confidence: 1,
    confidence_level: null,
    evaluation_details: null,
    evaluator_type: 'deterministic_rule',
    ai_provider: null,
    ai_model: null,
    prompt_template_version: null,
    kb_version: null,
    created_at: '2026-01-01T00:00:00Z',
    evidence: [],
    requirement_name: 'Question-to-CLO Mapping',
    dimension: 'CLO Alignment',
    source_type: 'Derived Exam Requirement',
    officiality: 'Derived',
    ...overrides,
  }
}

const CLOS: CloResponse[] = [
  {
    id: 'clo-1',
    analysis_id: 'analysis-1',
    code: 'CLO1',
    text: 'Explain core concepts.',
    program_outcome_reference: null,
    page_number: 1,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const TOPICS: TopicResponse[] = []
const ASSESSMENTS: AssessmentRecordResponse[] = [
  {
    id: 'assessment-1',
    analysis_id: 'analysis-1',
    method: 'Written examination',
    activity: 'Midterm',
    percentage: 30,
    page_number: 4,
    confidence: 1,
    geometry: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

function renderSection(
  overrides: Partial<React.ComponentProps<typeof AlignmentCoverageSection>> = {},
) {
  const onRetry = vi.fn()
  render(
    <AlignmentCoverageSection
      findings={ready([])}
      clos={ready(CLOS)}
      topics={ready(TOPICS)}
      assessmentRecords={ready(ASSESSMENTS)}
      lookups={buildLookups(CLOS, TOPICS, [])}
      unavailableLookups={new Set()}
      onRetry={onRetry}
      {...overrides}
    />,
  )
  return onRetry
}

describe('AlignmentCoverageSection', () => {
  it('shows only alignment findings and source-faithful extracted entities', () => {
    renderSection({
      findings: ready([
        finding({ id: 'f-clo', dimension: 'CLO Alignment' }),
        finding({
          id: 'f-marks',
          dimension: 'Marks and Totals',
          requirement_name: 'Correct Total Marks',
        }),
      ]),
    })

    expect(screen.getByText('Question-to-CLO Mapping')).toBeInTheDocument()
    expect(screen.queryByText('Correct Total Marks')).not.toBeInTheDocument()
    expect(screen.getByText('CLO1')).toBeInTheDocument()
    expect(screen.getByText('Written examination')).toBeInTheDocument()
    expect(screen.getByText(/source evidence only/i)).toBeInTheDocument()
  })

  it('keeps successful subsections visible when assessment records fail and retries only them', () => {
    const onRetry = renderSection({
      assessmentRecords: {
        status: 'error',
        message: 'Assessment records unavailable.',
      },
    })

    expect(screen.getByText('CLO1')).toBeInTheDocument()
    expect(screen.getByText(/assessment records unavailable/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledWith('assessmentRecords')
  })

  it('shows independent empty states without inventing mappings', () => {
    renderSection({
      findings: ready([]),
      clos: ready([]),
      topics: ready([]),
      assessmentRecords: ready([]),
    })

    expect(screen.getByText(/no alignment or coverage findings/i)).toBeInTheDocument()
    expect(screen.getByText(/no clos were extracted/i)).toBeInTheDocument()
    expect(screen.getByText(/no topics were extracted/i)).toBeInTheDocument()
    expect(screen.getByText(/no assessment records were extracted/i)).toBeInTheDocument()
  })
})
