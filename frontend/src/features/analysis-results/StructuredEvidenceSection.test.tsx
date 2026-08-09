import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { I18nProvider } from '../../i18n/I18nProvider'
import type {
  DocumentReferenceResponse,
  QuestionResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'
import { StructuredEvidenceSection } from './StructuredEvidenceSection'

vi.mock('../../api/analyses')

function question(number: number, page: number): QuestionResponse {
  return {
    id: `question-${number}`,
    analysis_id: 'analysis-1',
    parent_question_id: null,
    number_label: `Q${number}`,
    question_text: `Question ${number} source text`,
    page_number: page,
    marks: 6,
    sequence: number,
    confidence: 1,
    geometry: null,
    created_at: '2026-07-28T00:00:00Z',
  }
}

function material(
  id: string,
  type: SupportingMaterialResponse['material_type'],
  page: number,
  top: number,
): SupportingMaterialResponse {
  return {
    id,
    analysis_id: 'analysis-1',
    question_id: null,
    source_document: 'exam',
    material_type: type,
    page_number: page,
    source_text: type === 'code_block' ? 'def add_student():' : '',
    geometry: { x0: 10, top, x1: 200, bottom: top + 50 },
    confidence: 0.94,
    extraction_method: 'direct_text',
    created_at: `2026-07-28T00:00:${String(top).padStart(2, '0')}Z`,
  }
}

function annotation(
  id: string,
  materialId: string,
  type: 'label' | 'caption',
  text: string,
  normalizedLabel: string,
  page: number,
): SupportingMaterialAnnotationResponse {
  return {
    id,
    analysis_id: 'analysis-1',
    material_id: materialId,
    source_document: 'exam',
    annotation_type: type,
    original_text: text,
    normalized_label: normalizedLabel,
    page_number: page,
    geometry: null,
    confidence: 0.94,
    extraction_method: 'direct_text',
    created_at: '2026-07-28T00:00:00Z',
  }
}

function reference(
  questionNumber: number,
  originalText: string,
  normalizedLabel: string,
  resolution: DocumentReferenceResponse['resolution_status'],
  candidates: Array<{
    materialId: string
    exact: boolean
    selected?: boolean
  }>,
): DocumentReferenceResponse {
  return {
    id: `reference-${questionNumber}`,
    analysis_id: 'analysis-1',
    question_id: `question-${questionNumber}`,
    source_document: 'exam',
    target_type: normalizedLabel.startsWith('table')
      ? 'table'
      : normalizedLabel.startsWith('code')
        ? 'code_block'
        : 'figure',
    original_text: originalText,
    target_label: originalText,
    normalized_target_label: normalizedLabel,
    page_number: questionNumber === 3 || questionNumber === 4 ? 3 : questionNumber,
    geometry: null,
    confidence: 0.96,
    extraction_method: 'direct_text',
    resolution_status: resolution,
    association_candidates: candidates.map((candidate, index) => ({
      id: `candidate-${questionNumber}-${index}`,
      target_material_id: candidate.materialId,
      target_question_id: null,
      review_revision_id: 'revision-1',
      basis: candidate.exact
        ? 'exact_label'
        : candidate.selected
          ? 'deictic_geometry'
          : 'proximity_support',
      confidence: candidate.exact ? 0.94 : candidate.selected ? 0.85 : 0.5,
      proximity_distance: candidate.exact ? null : 20,
      exact_label_match: candidate.exact,
      selected: candidate.selected ?? false,
      ambiguity_reason: candidate.exact
        ? candidates.length > 1
          ? '2 exact targets share this label.'
          : null
        : candidate.selected
          ? null
          : 'Proximity is supporting evidence only.',
    })),
    created_at: '2026-07-28T00:00:00Z',
  }
}

const MATERIALS = [
  material('figure-1', 'figure', 2, 10),
  material('table-1', 'table', 3, 10),
  material('code-1', 'code_block', 3, 70),
  material('figure-2-network', 'figure', 5, 10),
  material('figure-2-flow', 'figure', 5, 70),
  material('diagram', 'figure', 6, 10),
]

const ANNOTATIONS = [
  annotation('f1-label', 'figure-1', 'label', 'الشكل 1: Relational Database Schema', 'figure:1', 2),
  annotation('f1-caption', 'figure-1', 'caption', 'الشكل 1: Relational Database Schema', 'figure:1', 2),
  annotation('t1-label', 'table-1', 'label', 'Table 1: Sample Student Scores', 'table:1', 3),
  annotation('t1-caption', 'table-1', 'caption', 'Sample Student Scores', 'table:1', 3),
  annotation('c1-label', 'code-1', 'label', 'Code 1: Parameterized Insert', 'code_block:1', 3),
  annotation('c1-caption', 'code-1', 'caption', 'Parameterized Insert', 'code_block:1', 3),
  annotation('f2n-label', 'figure-2-network', 'label', 'Figure 2: Network Structure', 'figure:2', 5),
  annotation('f2n-caption', 'figure-2-network', 'caption', 'Network Structure', 'figure:2', 5),
  annotation('f2v-label', 'figure-2-flow', 'label', 'Figure 2: Validation Flowchart', 'figure:2', 5),
  annotation('f2v-caption', 'figure-2-flow', 'caption', 'Validation Flowchart', 'figure:2', 5),
]

const REFERENCES = [
  reference(6, 'Figure 2', 'figure:2', 'ambiguous', [
    { materialId: 'figure-2-network', exact: true },
    { materialId: 'figure-2-flow', exact: true },
  ]),
  reference(2, 'الشكل 1', 'figure:1', 'resolved', [
    { materialId: 'figure-1', exact: true, selected: true },
  ]),
  reference(7, 'المخطط أدناه', 'figure:unlabeled', 'resolved', [
    { materialId: 'diagram', exact: false, selected: true },
  ]),
  reference(5, 'الشكل 5', 'figure:5', 'unresolved', []),
  reference(4, 'الكود 1', 'code_block:1', 'resolved', [
    { materialId: 'code-1', exact: true, selected: true },
  ]),
  reference(3, 'Table 1', 'table:1', 'resolved', [
    { materialId: 'table-1', exact: true, selected: true },
  ]),
]

beforeEach(() => {
  vi.clearAllMocks()
  window.localStorage.clear()
  vi.mocked(analysesApi.listSupportingMaterials).mockResolvedValue(MATERIALS)
  vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue(
    ANNOTATIONS,
  )
  vi.mocked(analysesApi.listDocumentReferences).mockResolvedValue(REFERENCES)
  vi.mocked(analysesApi.listQuestions).mockResolvedValue(
    [7, 6, 5, 4, 3, 2].map((number) =>
      question(number, number === 3 || number === 4 ? 3 : number),
    ),
  )
})

describe('StructuredEvidenceSection', () => {
  it('presents the approved Q2-Q7 question-centered relationship matrix', async () => {
    render(<StructuredEvidenceSection analysisId="analysis-1" />)

    const table = await screen.findByRole('table', {
      name: 'Question-to-material relationships',
    })
    expect(
      within(table).getAllByRole('rowheader').map((cell) => cell.textContent),
    ).toEqual(['Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7'])
    expect(within(table).getAllByText('Linked')).toHaveLength(3)
    expect(within(table).getByText('Faculty review only')).toBeInTheDocument()
    expect(within(table).getByText('Missing reference')).toBeInTheDocument()
    expect(within(table).getByText('Ambiguous reference')).toBeInTheDocument()
    expect(within(table).queryByText('Proximity-based link')).not.toBeInTheDocument()
    expect(within(table).getAllByText('Relational Database Schema').length)
      .toBeGreaterThan(0)
    expect(within(table).getAllByText('Sample Student Scores').length)
      .toBeGreaterThan(0)
    expect(within(table).getAllByText('Parameterized Insert').length)
      .toBeGreaterThan(0)
    expect(within(table).getByText('2 possible matches')).toBeInTheDocument()
    expect(screen.queryByText(/Labels and captions/)).not.toBeInTheDocument()
  })

  it('shows candidate materials and a concise reason only on demand', async () => {
    render(<StructuredEvidenceSection analysisId="analysis-1" />)

    const table = await screen.findByRole('table', {
      name: 'Question-to-material relationships',
    })
    const q6Row = within(table).getByRole('rowheader', { name: 'Q6' }).closest('tr')!
    const trigger = within(q6Row).getByRole('button', { name: 'View details' })
    fireEvent.click(trigger)

    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('Question 6 source text')).toHaveAttribute('dir', 'auto')
    expect(within(dialog).getByText('Network Structure')).toBeInTheDocument()
    expect(within(dialog).getByText('Validation Flowchart')).toBeInTheDocument()
    expect(within(dialog).getByText(
      'Q6 refers to Figure 2, but 2 distinct materials use that label.',
    )).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('keeps the relationship table and omits the duplicate physical inventory', async () => {
    render(<StructuredEvidenceSection analysisId="analysis-1" />)

    expect(
      await screen.findByRole('table', {
        name: 'Question-to-material relationships',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('table', { name: 'Physical material inventory' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/Physical material inventory/)).not.toBeInTheDocument()
  })

  it('uses the approved Arabic relationship labels and RTL headers', async () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    render(
      <I18nProvider>
        <StructuredEvidenceSection analysisId="analysis-1" />
      </I18nProvider>,
    )

    const table = await screen.findByRole('table', {
      name: 'علاقات الأسئلة بالمواد الداعمة',
    })
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(within(table).getByRole('columnheader', { name: 'العنصر المشار إليه' }))
      .toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'العنصر المطابق' }))
      .toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'نتيجة الربط' }))
      .toBeInTheDocument()
    expect(within(table).getAllByText('مرتبط')).toHaveLength(3)
    expect(within(table).getByText('للمراجعة الأكاديمية فقط')).toBeInTheDocument()
    expect(within(table).getByText('مرجع مفقود')).toBeInTheDocument()
    expect(within(table).getByText('مرجع غامض')).toBeInTheDocument()
  })

  it('keeps historical analyses compatible with empty collections', async () => {
    vi.mocked(analysesApi.listSupportingMaterials).mockResolvedValue([])
    vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue([])
    vi.mocked(analysesApi.listDocumentReferences).mockResolvedValue([])
    vi.mocked(analysesApi.listQuestions).mockResolvedValue([])

    render(<StructuredEvidenceSection analysisId="historical-analysis" />)

    expect(await screen.findByText('No structured supporting material'))
      .toBeInTheDocument()
  })

  it('shows a confirmed direct question-to-context link without an explicit reference phrase', async () => {
    vi.mocked(analysesApi.listSupportingMaterials).mockResolvedValue([
      { ...material('code-direct', 'code_block', 4, 10), question_id: 'question-4' },
    ])
    vi.mocked(analysesApi.listSupportingMaterialAnnotations).mockResolvedValue([])
    vi.mocked(analysesApi.listDocumentReferences).mockResolvedValue([])
    vi.mocked(analysesApi.listQuestions).mockResolvedValue([question(4, 4)])

    render(<StructuredEvidenceSection analysisId="analysis-direct" />)

    const table = await screen.findByRole('table', {
      name: 'Question-to-material relationships',
    })
    const q4Row = within(table).getByRole('rowheader', { name: 'Q4' }).closest('tr')!
    expect(q4Row).toHaveTextContent('Linked')
    expect(q4Row).toHaveTextContent('def add_student():')
    expect(screen.queryByText('No question-to-material references were identified.'))
      .not.toBeInTheDocument()
  })

})
