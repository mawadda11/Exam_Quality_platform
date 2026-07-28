import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { I18nProvider } from '../../i18n/I18nProvider'
import { StructuredEvidenceSection } from './StructuredEvidenceSection'

vi.mock('../../api/analyses')

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(analysesApi.listSupportingMaterials).mockResolvedValue([
    {
      id: 'material-1',
      analysis_id: 'analysis-1',
      question_id: 'question-1',
      source_document: 'exam',
      material_type: 'code_block',
      page_number: 2,
      source_text: 'SELECT student_id FROM results',
      geometry: { x0: 10, top: 20, x1: 200, bottom: 80 },
      confidence: 0.94,
      extraction_method: 'direct_text',
      created_at: '2026-07-28T00:00:00Z',
    },
  ])
  vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue([
    {
      id: 'annotation-1',
      analysis_id: 'analysis-1',
      material_id: 'material-1',
      source_document: 'exam',
      annotation_type: 'caption',
      original_text: 'Code 1: Example query',
      normalized_label: 'code_block:1',
      page_number: 2,
      geometry: null,
      confidence: 0.92,
      extraction_method: 'direct_text',
      created_at: '2026-07-28T00:00:00Z',
    },
  ])
  vi.mocked(analysesApi.listDocumentReferences).mockResolvedValue([
    {
      id: 'reference-1',
      analysis_id: 'analysis-1',
      question_id: 'question-1',
      source_document: 'exam',
      target_type: 'code_block',
      original_text: 'Refer to Code 1',
      target_label: 'Code 1',
      normalized_target_label: 'code_block:1',
      page_number: 1,
      geometry: null,
      confidence: 0.96,
      extraction_method: 'direct_text',
      resolution_status: 'unresolved',
      association_candidates: [
        {
          id: 'candidate-1',
          target_material_id: 'material-1',
          target_question_id: null,
          review_revision_id: null,
          basis: 'proximity_support',
          confidence: 0.5,
          proximity_distance: 42,
          exact_label_match: false,
          selected: false,
          ambiguity_reason: 'Proximity is supporting evidence only.',
        },
      ],
      created_at: '2026-07-28T00:00:00Z',
    },
  ])
})

describe('StructuredEvidenceSection', () => {
  it('shows original excerpts, provenance, and conservative resolution status', async () => {
    render(<StructuredEvidenceSection analysisId="analysis-1" />)

    expect(await screen.findByText('SELECT student_id FROM results')).toBeInTheDocument()
    expect(screen.getByText('Code 1: Example query')).toBeInTheDocument()
    expect(screen.getByText('Refer to Code 1')).toBeInTheDocument()
    expect(screen.getByText('Code 1')).toBeInTheDocument()
    expect(screen.getByText('unresolved')).toBeInTheDocument()
    expect(screen.getByText(/proximity candidates are retained/i)).toBeInTheDocument()
    expect(screen.getByText(/proximity_support/i)).toBeInTheDocument()
    expect(screen.getByText(/distance: 42/i)).toBeInTheDocument()
    expect(screen.getByText('94%')).toBeInTheDocument()
  })

  it('keeps historical analyses compatible with empty collections', async () => {
    vi.mocked(analysesApi.listSupportingMaterials).mockResolvedValue([])
    vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue([])
    vi.mocked(analysesApi.listDocumentReferences).mockResolvedValue([])

    render(<StructuredEvidenceSection analysisId="historical-analysis" />)

    expect(await screen.findByText('No structured supporting material')).toBeInTheDocument()
  })

  it('renders a logical mixed-language caption with bidi isolation', async () => {
    vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue([
      {
        id: 'annotation-ar-1',
        analysis_id: 'analysis-1',
        material_id: 'material-1',
        source_document: 'exam',
        annotation_type: 'caption',
        original_text: 'الشكل 1: Relational Database Schema',
        normalized_label: 'figure:1',
        page_number: 2,
        geometry: null,
        confidence: 0.92,
        extraction_method: 'direct_text',
        created_at: '2026-07-28T00:00:00Z',
      },
    ])

    render(<StructuredEvidenceSection analysisId="analysis-1" />)

    const caption = await screen.findByText('الشكل 1: Relational Database Schema')
    expect(caption.tagName).toBe('BDI')
    expect(caption).toHaveAttribute('dir', 'auto')
  })

  it('keeps the original excerpt behind an Arabic-labelled disclosure in RTL mode', async () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    render(
      <I18nProvider>
        <StructuredEvidenceSection analysisId="analysis-1" />
      </I18nProvider>,
    )

    const disclosures = await screen.findAllByText('عرض النص الأصلي')
    fireEvent.click(disclosures[0])
    expect(screen.getByText('SELECT student_id FROM results')).toBeInTheDocument()
    expect(screen.getByText('يُحفظ محتوى المصدر الأصلي لأغراض التدقيق.'))
      .toBeInTheDocument()
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
  })
})
