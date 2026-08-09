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
import {
  ExtractionReviewWorkspace,
  isReviewableUnassignedCandidate,
} from './ExtractionReviewWorkspace'

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
    blocking_extraction_warning_ids: [],
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(reviewResponse())
  vi.mocked(analysesApi.getExamPdf).mockResolvedValue(
    new Blob(['pdf'], { type: 'application/pdf' }),
  )
  vi.mocked(analysesApi.getExamPageImage).mockResolvedValue({
    blob: new Blob(['png'], { type: 'image/png' }),
    pageWidth: 612,
    pageHeight: 792,
  })
  vi.mocked(analysesApi.getCourseSpecificationPdf).mockResolvedValue(
    new Blob(['course-spec-pdf'], { type: 'application/pdf' }),
  )
  vi.mocked(analysesApi.getCourseSpecificationPageImage).mockResolvedValue({
    blob: new Blob(['course-spec-png'], { type: 'image/png' }),
    pageWidth: 612,
    pageHeight: 792,
  })
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:exam-preview')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
})

describe('ExtractionReviewWorkspace', () => {
  it('hides answer-space, table-header, and footer noise from unassigned candidates', () => {
    const candidate = (extractedText: string) => ({
      source_record_id: crypto.randomUUID(),
      included: true,
      question_source_record_id: null,
      source_document: 'exam' as const,
      evidence_type: 'extraction_candidate_local_local_only',
      page_number: 1,
      item_reference: '',
      extracted_text: extractedText,
      extraction_confidence: 1,
      geometry: null,
    })

    expect(isReviewableUnassignedCandidate(candidate('............................'))).toBe(false)
    expect(isReviewableUnassignedCandidate(candidate('No. Statement T / F'))).toBe(false)
    expect(
      isReviewableUnassignedCandidate(
        candidate('Synthetic test fixture - not an official document | 1 / 4'),
      ),
    ).toBe(false)
    expect(
      isReviewableUnassignedCandidate(
        candidate('Explain why a foreign key may contain NULL.'),
      ),
    ).toBe(true)
    expect(
      isReviewableUnassignedCandidate(candidate('Calculate 1 / 4 of the available records.')),
    ).toBe(true)
  })

  it('renders the loading state while the review request is still pending', () => {
    vi.mocked(analysesApi.getExtractionReview).mockReturnValue(new Promise(() => undefined))

    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Loading extraction review')).toBeInTheDocument()
  })

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

  it('shows the Course Specification PDF on the left with selectable copy mode for CLO review', async () => {
    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('tab', { name: /CLOs \(1\)/ }))

    expect(await screen.findByLabelText('Original Course Specification PDF')).toBeInTheDocument()
    await waitFor(() => {
      expect(analysesApi.getCourseSpecificationPdf).toHaveBeenCalledWith('analysis-1')
      expect(analysesApi.getCourseSpecificationPageImage).toHaveBeenCalled()
    })
    expect(screen.getByText('Review against the Course Specification PDF')).toBeInTheDocument()

    fireEvent.click(await screen.findByRole('button', { name: 'Copy text' }))
    expect(
      await screen.findByLabelText('Selectable Course Specification PDF — Page 2'),
    ).toBeInTheDocument()
  })

  it('lets the reviewer add missing CLO and topic records without replacing extracted records', async () => {
    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('tab', { name: /CLOs \(1\)/ }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Add missing CLO from Course Specification PDF' }),
    )

    const cloCodes = screen.getAllByLabelText('CLO code')
    const cloTexts = screen.getAllByLabelText('CLO text')
    expect(cloCodes).toHaveLength(2)
    expect(cloCodes[1]).toHaveValue('')
    expect(cloTexts[1]).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Save New Revision' })).toBeDisabled()

    fireEvent.click(screen.getByRole('tab', { name: /Topics \(0\)/ }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Add missing topic from Course Specification PDF' }),
    )

    expect(screen.getByLabelText('Topic code')).toHaveValue('')
    expect(screen.getByLabelText('Topic text')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Save New Revision' })).toBeDisabled()
    expect(analysesApi.getCourseSpecificationPdf).toHaveBeenCalled()
  })

  it('moves the raster PDF preview to the selected question geometry', async () => {
    const locatedSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    locatedSnapshot.questions[0].page_number = 2
    locatedSnapshot.questions[0].geometry = { x0: 60, top: 90, x1: 320, bottom: 130 }
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot: locatedSnapshot,
        original_snapshot: structuredClone(locatedSnapshot),
        warnings: [],
      }),
    )

    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    const showButtons = await screen.findAllByRole('button', { name: 'Show in PDF' })
    fireEvent.click(showButtons[0])

    expect(await screen.findByText('Selected PDF location: Page 2')).toBeInTheDocument()
    expect(analysesApi.getExamPageImage).toHaveBeenCalledWith(
      'analysis-1',
      2,
      null,
      { dpi: 144 },
    )
    expect(await screen.findByRole('img', {
      name: 'Original examination PDF — Page 2',
    })).toBeInTheDocument()
  })

  it('adds a missing visual question as an incomplete human-review draft', async () => {
    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('button', { name: 'Add missing question from PDF' }))

    expect(await screen.findByText('Complete the added question')).toBeInTheDocument()
    expect(screen.getByLabelText('Question number')).toHaveValue('')
    expect(screen.getByLabelText('Question text')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Save New Revision' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Confirm Extraction and Continue' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Remove added question' })).toBeInTheDocument()
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
      {
        source_record_id: '60000000-0000-0000-0000-000000000002',
        included: true,
        material_source_record_id: '50000000-0000-0000-0000-000000000001',
        source_document: 'exam',
        annotation_type: 'caption',
        original_text: 'Figure 1: Relational Database Schema',
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

    fireEvent.click(await screen.findByRole('tab', { name: /linked supporting context/i }))
    expect(screen.getByLabelText('Reference label')).toHaveValue('Figure 1')
    expect(screen.getByLabelText('Caption or title')).toHaveValue(
      'Relational Database Schema',
    )
    expect(screen.getByText('Refer to Figure 1')).toBeInTheDocument()
    expect(screen.getByLabelText('Target label')).toHaveValue('Figure 1')
    expect(screen.queryByText(/Labels and captions/i)).not.toBeInTheDocument()
    expect(screen.getAllByLabelText('Include in analysis')).toHaveLength(1)
    expect(screen.getByText(/association review details/i)).toBeInTheDocument()
    expect(screen.getByText(/uniquely linked material/i)).toBeInTheDocument()
  })

  it('edits and saves logical Arabic and English annotation text with bidi isolation', async () => {
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
        original_text: 'الشكل 1',
        normalized_label: 'figure:1',
        page_number: 2,
        extraction_confidence: 0.93,
        extraction_method: 'direct_text',
        geometry: null,
      },
      {
        source_record_id: '60000000-0000-0000-0000-000000000002',
        included: true,
        material_source_record_id: '50000000-0000-0000-0000-000000000001',
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

    fireEvent.click(await screen.findByRole('tab', { name: /linked supporting context/i }))
    const label = screen.getByLabelText('Reference label')
    const annotation = screen.getByLabelText('Caption or title')
    expect(label).toHaveValue('الشكل 1')
    expect(annotation).toHaveValue('Relational Database Schema')
    expect(annotation).toHaveAttribute('dir', 'auto')
    expect(annotation).toHaveClass('bidi-plaintext')
    fireEvent.change(annotation, {
      target: { value: 'Relational Database Schema — reviewed' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Restore machine value' }))
    expect(screen.getByLabelText('Caption or title')).toHaveValue(
      'Relational Database Schema',
    )
    fireEvent.change(screen.getByLabelText('Caption or title'), {
      target: { value: 'Relational Database Schema — reviewed' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save new revision/i }))

    await waitFor(() =>
      expect(analysesApi.saveExtractionReview).toHaveBeenCalledWith(
        'analysis-1',
        '40000000-0000-0000-0000-000000000001',
        expect.objectContaining({
          supporting_annotations: [
            expect.objectContaining({
              original_text: 'الشكل 1',
            }),
            expect.objectContaining({
              original_text: 'Relational Database Schema — reviewed',
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
    fireEvent.click(screen.getByRole('button', { name: 'Review question' }))
    const parentSelector = screen.getByLabelText('Parent question')
    expect(parentSelector).toHaveValue('10000000-0000-0000-0000-000000000010')
    fireEvent.change(parentSelector, { target: { value: '' } })
    expect(parentSelector).toHaveValue('')
  })

  it('shows local and Gemini candidates and lets a reviewer correct an existing blank', async () => {
    const candidateSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    candidateSnapshot.schema_version = 2
    candidateSnapshot.questions[0].question_type = 'fill_in_blank'
    candidateSnapshot.question_blanks = [
      {
        source_record_id: '80000000-0000-0000-0000-000000000001',
        included: true,
        question_source_record_id: '10000000-0000-0000-0000-000000000001',
        blank_index: 1,
        source_text: '____',
        page_number: 1,
        geometry: { x0: 40, top: 50, x1: 90, bottom: 60 },
      },
    ]
    candidateSnapshot.evidence.push(
      {
        source_record_id: '81000000-0000-0000-0000-000000000001',
        included: true,
        question_source_record_id: '10000000-0000-0000-0000-000000000001',
        source_document: 'exam',
        evidence_type: 'extraction_candidate_local_local_only',
        page_number: 1,
        item_reference: 'local-1',
        extracted_text: 'Explain a stack.',
        extraction_confidence: 0.7,
        geometry: null,
      },
      {
        source_record_id: '81000000-0000-0000-0000-000000000002',
        included: true,
        question_source_record_id: '10000000-0000-0000-0000-000000000001',
        source_document: 'exam',
        evidence_type: 'extraction_candidate_gemini_cache',
        page_number: 1,
        item_reference: 'gemini-1',
        extracted_text: 'Explain a stack.',
        extraction_confidence: 0.9,
        geometry: null,
      },
    )
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot: candidateSnapshot,
        original_snapshot: structuredClone(candidateSnapshot),
        warnings: [],
      }),
    )

    render(<ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />)

    expect(await screen.findByText('Extraction candidates')).toBeInTheDocument()
    expect(screen.getByText(/local \/ local_only/)).toBeInTheDocument()
    expect(screen.getByText(/Gemini \/ cache/)).toBeInTheDocument()
    const blank = screen.getByLabelText('Blank source text 1')
    expect(blank).toHaveValue('____')
    fireEvent.change(blank, { target: { value: '( )' } })
    expect(blank).toHaveValue('( )')
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

describe('ExtractionReviewWorkspace extraction failure presentation', () => {
  it('shows a dedicated zero-question failure state and groups repeated warnings', async () => {
    const failedSnapshot = structuredClone(ORIGINAL_SNAPSHOT)
    failedSnapshot.schema_version = 2
    failedSnapshot.questions = []
    failedSnapshot.evidence = []
    failedSnapshot.extraction_warnings = [
      {
        source_record_id: '90000000-0000-0000-0000-000000000001',
        code: 'UNASSIGNED_CONTENT',
        severity: 'critical',
        page_number: 1,
        source_line_ids: ['P1-L1'],
        message: 'OCR content could not be assigned safely to native PDF content.',
        geometry: null,
        resolved: false,
      },
      {
        source_record_id: '90000000-0000-0000-0000-000000000002',
        code: 'UNASSIGNED_CONTENT',
        severity: 'critical',
        page_number: 1,
        source_line_ids: ['P1-L2'],
        message: 'OCR content could not be assigned safely to native PDF content.',
        geometry: null,
        resolved: false,
      },
    ]
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot: failedSnapshot,
        original_snapshot: structuredClone(failedSnapshot),
        can_confirm: false,
        warnings: [],
        confirmation_blockers: ['No reliable exam questions were extracted.'],
      }),
    )

    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Exam extraction needs another attempt')).toBeInTheDocument()
    expect(screen.getByText(/2 records/i)).toBeInTheDocument()
    expect(screen.getAllByText('UNASSIGNED_CONTENT')).toHaveLength(1)
    expect(screen.getByRole('button', { name: /confirm extraction and continue/i })).toBeDisabled()
  })
})

describe('simplified question review', () => {
  it('keeps advisory reconciliation visible without disabling confirmation or requiring resolution', async () => {
    const snapshot = structuredClone(ORIGINAL_SNAPSHOT)
    snapshot.schema_version = 2
    snapshot.question_source_spans = [
      {
        source_record_id: '91000000-0000-0000-0000-000000000001',
        question_source_record_id: snapshot.questions[0].source_record_id,
        option_source_record_id: null,
        provider: 'gemini',
        provider_version: null,
        source_line_id: 'P1-L1',
        page_number: 1,
        original_text: 'Explain a stack.',
        geometry: null,
        extraction_confidence: 0.9,
        extraction_method: 'gemini',
      },
    ]
    snapshot.extraction_warnings = Array.from({ length: 20 }, (_, index) => ({
        source_record_id: `90000000-0000-0000-0000-${String(index + 1).padStart(12, '0')}`,
        code: 'MARKS_MISMATCH',
        severity: 'critical',
        page_number: 1,
        source_line_ids: ['P1-L1'],
        message: 'The extraction sources proposed different visible marks.',
        geometry: null,
        resolved: false,
      }))
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot,
        original_snapshot: structuredClone(snapshot),
        warnings: [],
        can_confirm: true,
        confirmation_blockers: [],
        blocking_extraction_warning_ids: [],
      }),
    )

    const { container } = render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Review the extracted questions')).toBeInTheDocument()
    expect(screen.queryByText('Needs review')).not.toBeInTheDocument()
    expect(screen.queryByText('questions needing review')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Review flagged questions' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Technical extraction details/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Check the section and child marks against the PDF.')).not.toBeInTheDocument()
    const continueButton = screen.getByRole('button', { name: /confirm extraction and continue/i })
    expect(continueButton).toBeEnabled()
    expect(screen.queryByRole('checkbox', { name: /resolve all warnings/i })).not.toBeInTheDocument()
    fireEvent.click(continueButton)
    expect(screen.queryByRole('dialog', { name: 'Continue with review recommendations?' })).not.toBeInTheDocument()
    expect(container.querySelectorAll('.review-reconciliation-warning')).toHaveLength(1)
  })

  it('uses the full PDF preview instead of a separate question crop', async () => {
    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Use the PDF as the source reference')).toBeInTheDocument()
    expect(screen.queryByText('Original question from PDF')).not.toBeInTheDocument()
  })

  it('allows a reviewer to correct or clear marks on a container question', async () => {
    const snapshot = structuredClone(ORIGINAL_SNAPSHOT)
    snapshot.questions[0].marks = 19
    snapshot.questions.push({
      ...snapshot.questions[0],
      source_record_id: '10000000-0000-0000-0000-000000000002',
      parent_source_record_id: snapshot.questions[0].source_record_id,
      number_label: 'Q1(a)',
      question_text: 'Explain one property.',
      marks: 2,
      sequence: 2,
    })
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot,
        original_snapshot: structuredClone(snapshot),
        warnings: [],
      }),
    )

    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    const marks = await screen.findByLabelText('Marks')
    expect(marks).toBeEnabled()
    expect(marks).toHaveValue(19)
    fireEvent.change(marks, { target: { value: '' } })
    expect(marks).toHaveValue(null)
  })

  it('shows null child marks as covered by the authoritative section total', async () => {
    const snapshot = structuredClone(ORIGINAL_SNAPSHOT)
    snapshot.questions[0].marks = 5
    snapshot.questions.push({
      ...snapshot.questions[0],
      source_record_id: '10000000-0000-0000-0000-000000000002',
      parent_source_record_id: snapshot.questions[0].source_record_id,
      number_label: 'Q2(a)',
      question_text: 'State whether the claim is true.',
      marks: null,
      sequence: 2,
    })
    vi.mocked(analysesApi.getExtractionReview).mockResolvedValue(
      reviewResponse({
        snapshot,
        original_snapshot: structuredClone(snapshot),
        warnings: [],
      }),
    )

    render(
      <MemoryRouter>
        <ExtractionReviewWorkspace analysisId="analysis-1" onConfirmed={vi.fn()} />
      </MemoryRouter>,
    )

    expect(await screen.findByText('No individual mark specified; section total: 5'))
      .toBeInTheDocument()
    expect(screen.getByText(/individual child marks may remain blank/i)).toBeInTheDocument()
    expect(screen.queryByText('Sub-question marks total:')).not.toBeInTheDocument()
  })
})
