import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type {
  ExtractionReviewConfirmResponse,
  ExtractionReviewResponse,
  ExtractionReviewSnapshot,
} from '../../types/api'
import { ExtractionReviewWorkspace } from './ExtractionReviewWorkspace'

vi.mock('../../api/analyses')

const ORIGINAL_SNAPSHOT: ExtractionReviewSnapshot = {
  schema_version: 1,
  questions: [
    {
      source_record_id: '10000000-0000-0000-0000-000000000001',
      included: true,
      parent_source_record_id: null,
      number_label: 'Q1',
      question_text: 'Explain a stack.',
      page_number: 1,
      marks: 5,
      sequence: 1,
      extraction_confidence: 0.66,
      geometry: null,
    },
  ],
  evidence: [
    {
      source_record_id: '20000000-0000-0000-0000-000000000001',
      included: true,
      question_source_record_id: '10000000-0000-0000-0000-000000000001',
      source_document: 'exam',
      evidence_type: 'question_text',
      page_number: 1,
      item_reference: 'Q1',
      extracted_text: 'Explain a stack.',
      extraction_confidence: 0.66,
      geometry: null,
    },
  ],
  clos: [
    {
      source_record_id: '30000000-0000-0000-0000-000000000001',
      included: true,
      code: 'CLO1',
      text: 'Explain data structures.',
      program_outcome_reference: 'P1',
      page_number: 2,
      extraction_confidence: 0.95,
      geometry: null,
    },
  ],
  topics: [],
  assessment_records: [],
}

function reviewResponse(
  overrides: Partial<ExtractionReviewResponse> = {},
): ExtractionReviewResponse {
  return {
    analysis_id: 'analysis-1',
    revision_id: '40000000-0000-0000-0000-000000000001',
    revision_number: 1,
    created_at: '2026-07-26T00:00:00Z',
    snapshot: structuredClone(ORIGINAL_SNAPSHOT),
    original_snapshot: structuredClone(ORIGINAL_SNAPSHOT),
    confirmed_revision_id: null,
    is_confirmed: false,
    can_edit: true,
    can_confirm: true,
    warnings: [
      {
        code: 'low_extraction_confidence',
        severity: 'warning',
        collection: 'questions',
        source_record_id: '10000000-0000-0000-0000-000000000001',
        message: 'This question has low machine-extraction confidence.',
      },
    ],
    confirmation_blockers: [],
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(reviewResponse())
})

describe('ExtractionReviewWorkspace', () => {
  it('loads the latest immutable revision and exposes source anchors and warnings', async () => {
    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Revision 1')).toBeInTheDocument()
    expect(screen.getByText('Page 1 · 66% extraction confidence')).toBeInTheDocument()
    expect(screen.getByText(/low machine-extraction confidence/i)).toBeInTheDocument()
    expect(analysesApi.getExtractionReview).toHaveBeenCalledWith('analysis-1')
    expect(screen.getByRole('link', { name: /learn how this works/i })).toHaveAttribute(
      'href',
      '/evaluation-scope#extraction-review',
    )
  })

  it('shows structured source records and all association candidates for review', async () => {
    const structuredSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    structuredSnapshot.supporting_materials = [
      {
        source_record_id: '50000000-0000-0000-0000-000000000001',
        included: true,
        question_source_record_id: '10000000-0000-0000-0000-000000000001',
        source_document: 'exam',
        material_type: 'figure',
        source_text: '',
        page_number: 2,
        extraction_confidence: 0.94,
        extraction_method: 'direct_text',
        geometry: null,
      },
    ]
    structuredSnapshot.supporting_annotations = [
      {
        source_record_id: '60000000-0000-0000-0000-000000000001',
        included: true,
        material_source_record_id: '50000000-0000-0000-0000-000000000001',
        source_document: 'exam',
        annotation_type: 'label',
        original_text: 'Figure 1',
        normalized_label: 'figure:1',
        page_number: 2,
        extraction_confidence: 0.93,
        extraction_method: 'direct_text',
        geometry: null,
      },
    ]
    structuredSnapshot.document_references = [
      {
        source_record_id: '70000000-0000-0000-0000-000000000001',
        included: true,
        question_source_record_id: '10000000-0000-0000-0000-000000000001',
        source_document: 'exam',
        target_type: 'figure',
        original_text: 'Refer to Figure 1',
        target_label: 'Figure 1',
        normalized_target_label: 'figure:1',
        resolution_status: 'resolved',
        page_number: 1,
        extraction_confidence: 0.96,
        extraction_method: 'direct_text',
        geometry: null,
      },
    ]
    structuredSnapshot.reference_associations = [
      {
        source_record_id: '80000000-0000-0000-0000-000000000001',
        reference_source_record_id: '70000000-0000-0000-0000-000000000001',
        target_material_source_record_id: '50000000-0000-0000-0000-000000000001',
        target_question_source_record_id: null,
        basis: 'exact_label',
        extraction_confidence: 0.93,
        proximity_distance: null,
        exact_label_match: true,
        selected: true,
        ambiguity_reason: null,
      },
    ]
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot: structuredSnapshot,
        original_snapshot: structuredClone(structuredSnapshot),
      }),
    )

    render(
      <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />,
    )

    fireEvent.click(await screen.findByRole('tab', { name: /materials & references/i }))
    expect(screen.getByText('Figure 1')).toBeInTheDocument()
    expect(screen.getByText('Refer to Figure 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Target label')).toHaveValue('Figure 1')
    expect(screen.getByText(/exact_label/i)).toBeInTheDocument()
    expect(screen.getByText(/selected exact target/i)).toBeInTheDocument()
  })

  it('edits and saves logical Arabic and English annotation text with bidi isolation', async () => {
    const structuredSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    structuredSnapshot.supporting_annotations = [
      {
        source_record_id: '60000000-0000-0000-0000-000000000001',
        included: true,
        material_source_record_id: null,
        source_document: 'exam',
        annotation_type: 'caption',
        original_text: 'الشكل 1: Relational Database Schema',
        normalized_label: 'figure:1',
        page_number: 2,
        extraction_confidence: 0.93,
        extraction_method: 'direct_text',
        geometry: null,
      },
    ]
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot: structuredSnapshot,
        original_snapshot: structuredClone(structuredSnapshot),
      }),
    )
    vi.mocked(analysesApi.saveExtractionReview).mockResolvedValue(
      reviewResponse({
        revision_id: '40000000-0000-0000-0000-000000000002',
        revision_number: 2,
        snapshot: structuredSnapshot,
      }),
    )

    render(<ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />)

    fireEvent.click(await screen.findByRole('tab', { name: /materials & references/i }))
    const annotation = screen.getByLabelText('Extracted text')
    expect(annotation).toHaveValue('الشكل 1: Relational Database Schema')
    expect(annotation).toHaveAttribute('dir', 'auto')
    expect(annotation).toHaveClass('bidi-plaintext')
    fireEvent.change(annotation, {
      target: { value: 'الشكل 1: Relational Database Schema — reviewed' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save new revision/i }))

    await waitFor(() =>
      expect(analysesApi.saveExtractionReview).toHaveBeenCalledWith(
        'analysis-1',
        '40000000-0000-0000-0000-000000000001',
        expect.objectContaining({
          supporting_annotations: [
            expect.objectContaining({
              original_text: 'الشكل 1: Relational Database Schema — reviewed',
            }),
          ],
        }),
      ),
    )
  })

  it('requires saving a new revision before confirming edited extraction text', async () => {
    const correctedSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    correctedSnapshot.questions[0].question_text = 'Explain the stack data structure.'
    vi.mocked(analysesApi.saveExtractionReview).mockResolvedValue(
      reviewResponse({
        revision_id: '40000000-0000-0000-0000-000000000002',
        revision_number: 2,
        snapshot: correctedSnapshot,
        warnings: [],
      }),
    )
    const confirmation: ExtractionReviewConfirmResponse = {
      analysis_id: 'analysis-1',
      confirmed_revision_id: '40000000-0000-0000-0000-000000000002',
      confirmed_revision_number: 2,
      state: 'building_evidence',
    }
    vi.mocked(analysesApi.confirmExtractionReview).mockResolvedValue(confirmation)
    const onConfirmed = vi.fn()

    render(
      <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={onConfirmed} />,
    )

    const textArea = await screen.findByLabelText('Question text')
    fireEvent.change(textArea, {
      target: { value: 'Explain the stack data structure.' },
    })

    expect(screen.getByRole('button', { name: /confirm extraction/i })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /save new revision/i }))

    await waitFor(() =>
      expect(analysesApi.saveExtractionReview).toHaveBeenCalledWith(
        'analysis-1',
        '40000000-0000-0000-0000-000000000001',
        expect.objectContaining({
          questions: [
            expect.objectContaining({
              question_text: 'Explain the stack data structure.',
            }),
          ],
        }),
      ),
    )
    expect(await screen.findByText('Revision 2 saved.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /confirm extraction/i }))
    await waitFor(() =>
      expect(analysesApi.confirmExtractionReview).toHaveBeenCalledWith(
        'analysis-1',
        '40000000-0000-0000-0000-000000000002',
      ),
    )
    expect(onConfirmed).toHaveBeenCalledWith(confirmation)
  })

  it('keeps the review focused on questions, CLOs, and topics while preserving internal evidence', async () => {
    const excludedSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    excludedSnapshot.questions[0].included = false
    excludedSnapshot.evidence[0].included = false
    vi.mocked(analysesApi.saveExtractionReview).mockResolvedValue(
      reviewResponse({
        revision_id: '40000000-0000-0000-0000-000000000002',
        revision_number: 2,
        snapshot: excludedSnapshot,
      }),
    )

    render(
      <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />,
    )

    const textArea = await screen.findByLabelText('Question text')
    fireEvent.change(textArea, { target: { value: 'Temporary correction' } })
    fireEvent.click(screen.getByRole('button', { name: 'Restore machine value' }))
    expect(screen.getByLabelText('Question text')).toHaveValue('Explain a stack.')

    expect(screen.queryByRole('tab', { name: /assessment/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: /evidence/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Include in analysis' }))
    expect(screen.getByLabelText('Question text')).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: /save new revision/i }))

    await waitFor(() =>
      expect(analysesApi.saveExtractionReview).toHaveBeenCalledWith(
        'analysis-1',
        '40000000-0000-0000-0000-000000000001',
        expect.objectContaining({
          questions: [expect.objectContaining({ included: false })],
          evidence: [expect.objectContaining({ included: false })],
        }),
      ),
    )
  })

  it('keeps a container question selected while allowing child questions to be reviewed independently', async () => {
    const hierarchySnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    hierarchySnapshot.questions = [
      {
        source_record_id: '10000000-0000-0000-0000-000000000010',
        included: true,
        parent_source_record_id: null,
        number_label: 'Q2',
        question_text: 'Answer the following.',
        page_number: 1,
        marks: null,
        sequence: 1,
        extraction_confidence: 0.9,
        geometry: null,
      },
      {
        source_record_id: '10000000-0000-0000-0000-000000000011',
        included: true,
        parent_source_record_id: '10000000-0000-0000-0000-000000000010',
        number_label: 'Q2(a)',
        question_text: 'Explain normalization.',
        page_number: 1,
        marks: 4,
        sequence: 2,
        extraction_confidence: 0.9,
        geometry: null,
      },
    ]
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot: hierarchySnapshot,
        original_snapshot: structuredClone(hierarchySnapshot),
        warnings: [],
      }),
    )

    render(<ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />)

    expect(
  (await screen.findAllByText('Parent / Container Question')).length,
).toBeGreaterThan(0)
    expect(screen.getByText(/not scored as an independent semantic item/i)).toBeInTheDocument()
    expect(screen.getByText(/sub-question marks total/i)).toHaveTextContent('4')
    const includeControls = screen.getAllByRole('checkbox', { name: 'Include in analysis' })
    expect(includeControls[0]).toBeDisabled()
    expect(includeControls[1]).toBeEnabled()
  })

  it('shows a safe API conflict and keeps the draft available for review', async () => {
    vi.mocked(analysesApi.saveExtractionReview).mockRejectedValue(
      new ApiError(409, 'The extraction review changed. Reload the latest revision.'),
    )
    render(
      <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />,
    )

    fireEvent.change(await screen.findByLabelText('Question text'), {
      target: { value: 'Corrected text' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save new revision/i }))

    expect(await screen.findByText(/changed\. reload the latest revision/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Question text')).toHaveValue('Corrected text')
  })
})
