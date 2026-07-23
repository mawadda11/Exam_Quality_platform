import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { FindingEvidenceRef } from '../../types/api'
import { EvidenceDrillDown } from './EvidenceDrillDown'
import { buildLookups } from './lookups'

function evidence(overrides: Partial<FindingEvidenceRef> = {}): FindingEvidenceRef {
  return {
    id: 'ev-1',
    source_document: 'exam',
    evidence_type: 'question_text',
    page_number: 2,
    item_reference: 'Q1',
    ...overrides,
  }
}

describe('EvidenceDrillDown', () => {
  it('shows a neutral message when Not Applicable and no evidence is linked', () => {
    render(<EvidenceDrillDown evidence={[]} status="Not Applicable" lookups={buildLookups([], [], [])} />)
    expect(screen.getByText(/does not apply in this case/i)).toBeInTheDocument()
  })

  it('shows an explicit absence message for any other status with no evidence', () => {
    render(<EvidenceDrillDown evidence={[]} status="Not Verified" lookups={buildLookups([], [], [])} />)
    expect(screen.getByText(/no evidence was linked/i)).toBeInTheDocument()
  })

  it('resolves a CLO evidence item to its full citable text via the deterministic code join', () => {
    const lookups = buildLookups(
      [
        {
          id: 'clo-1',
          analysis_id: 'a1',
          code: 'CLO2',
          text: 'Apply data structures to solve problems.',
          program_outcome_reference: null,
          page_number: 1,
          confidence: 1,
          geometry: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
      [],
      [],
    )
    render(
      <EvidenceDrillDown
        evidence={[
          evidence({
            evidence_type: 'clo',
            item_reference: 'CLO2',
            page_number: 3,
            source_document: 'tp153',
          }),
        ]}
        status="Satisfied"
        lookups={lookups}
      />,
    )
    expect(
      screen.getByText(/CLO CLO2: Apply data structures to solve problems\. \(TP-153 p\.3\)/),
    ).toBeInTheDocument()
  })

  it('falls back to the bare code when no matching CLO/topic/question is found', () => {
    render(
      <EvidenceDrillDown
        evidence={[
          evidence({ evidence_type: 'clo', item_reference: 'CLO9', source_document: 'tp153' }),
        ]}
        status="Satisfied"
        lookups={buildLookups([], [], [])}
      />,
    )
    expect(screen.getByText(/CLO CLO9 \(TP-153 p\.2\)/)).toBeInTheDocument()
  })

  it('labels an unrecognized evidence_type with the raw value rather than failing', () => {
    render(
      <EvidenceDrillDown
        evidence={[evidence({ evidence_type: 'future_evidence_type', item_reference: 'X' })]}
        status="Satisfied"
        lookups={buildLookups([], [], [])}
      />,
    )
    expect(screen.getByText(/future_evidence_type: X/)).toBeInTheDocument()
  })
})
