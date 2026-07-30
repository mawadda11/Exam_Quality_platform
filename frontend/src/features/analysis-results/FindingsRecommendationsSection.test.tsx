import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { FindingsRecommendationsSection } from './FindingsRecommendationsSection'
import { buildLookups } from './lookups'

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

const LOOKUPS = buildLookups([], [], [])

function renderSection(
  findings: FindingResponse[],
  recommendations: RecommendationResponse[] = [],
  translated = false,
) {
  const byFinding = new Map<string, RecommendationResponse[]>()
  for (const recommendation of recommendations) {
    byFinding.set(recommendation.finding_id, [recommendation])
  }
  const tree = (
    <MemoryRouter>
      <FindingsRecommendationsSection
        findings={findings}
        recommendations={{ status: 'ready', data: recommendations }}
        recommendationsByFinding={byFinding}
        lookups={LOOKUPS}
        onRetryRecommendations={vi.fn()}
      />
    </MemoryRouter>
  )
  return render(translated ? <I18nProvider>{tree}</I18nProvider> : tree)
}

beforeEach(() => {
  window.localStorage.clear()
})

describe('FindingsRecommendationsSection', () => {
  it('shows one exact insufficient-evidence explanation without a duplicate result list', () => {
    renderSection([
      finding({ id: 'f-ok', status: 'Satisfied' }),
      finding({
        id: 'f-missing',
        status: 'Not Verified',
        requirement_name: 'Applicable CLO Coverage',
        explanation: 'No usable CLO evidence was available.',
      }),
    ])

    expect(
      screen.getByRole('heading', {
        name: 'Insufficient Evidence — Excluded from the Score (1)',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getAllByText(
        'The available evidence was insufficient for a reliable judgment, so these results were excluded from the score and were not treated as unmet requirements.',
      ),
    ).toHaveLength(1)
    expect(screen.getAllByText('Applicable CLO Coverage')).toHaveLength(1)
  })

  it('prioritizes attention strictly and collapses Satisfied and Not Applicable', () => {
    renderSection([
      finding({
        id: 'satisfied',
        status: 'Satisfied',
        requirement_name: 'Satisfied result',
      }),
      finding({
        id: 'partial',
        status: 'Partially Satisfied',
        requirement_name: 'Partial result',
      }),
      finding({
        id: 'failed',
        status: 'Not Satisfied',
        requirement_name: 'Unmet result',
      }),
      finding({
        id: 'unverified',
        status: 'Not Verified',
        requirement_name: 'Unverified result',
      }),
      finding({
        id: 'na',
        status: 'Not Applicable',
        requirement_name: 'Not applicable result',
      }),
    ])

    const attention = screen.getByRole('heading', { name: 'Requires attention' })
      .closest('section')!
    const cards = [...attention.querySelectorAll('.finding-card')]
    expect(cards.map((card) => card.textContent)).toEqual([
      expect.stringContaining('Unmet result'),
      expect.stringContaining('Partial result'),
      expect.stringContaining('Unverified result'),
    ])
    expect(screen.getByText('Satisfied findings (1)').closest('details'))
      .not.toHaveAttribute('open')
    expect(screen.getByText('Not Applicable findings (1)').closest('details'))
      .not.toHaveAttribute('open')
  })

  it('shows recommendations and specialized links without duplicating alignment content', () => {
    const alignment = finding({
      id: 'alignment',
      status: 'Partially Satisfied',
      requirement_name: 'Alignment action',
      evidence: [
        {
          id: 'question-source',
          source_document: 'exam',
          evidence_type: 'question_text',
          page_number: 2,
          item_reference: 'Q2',
        },
      ],
    })
    const recommendation: RecommendationResponse = {
      finding_id: 'alignment',
      requirement_id: 'REQ001',
      rule_id: 'RULE001',
      status: 'Partially Satisfied',
      recommendation_id: 'REC001',
      title: 'Review the suggested relationship',
      text: 'Confirm the relationship against the Course Specification.',
      target_user: 'Faculty',
      recommendation_type: 'Corrective',
    }
    const { container } = renderSection([alignment], [recommendation])

    expect(screen.getByText('Included with partial credit.')).toBeInTheDocument()
    expect(screen.getByText('Review the suggested relationship')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'View details in Alignment & Coverage' }),
    ).toHaveAttribute(
      'href',
      '/analyses/analysis-1/results/alignment-coverage',
    )
    expect(screen.queryByText('Evidence and original excerpts'))
      .not.toBeInTheDocument()
    expect(screen.queryByText('View direct evidence')).not.toBeInTheDocument()
    expect(container.querySelector('table')).not.toBeInTheDocument()
  })

  it('removes repeated determination panels and adds one page-level methodology note and link', () => {
    const { container } = renderSection([
      finding({
        id: 'semantic-1',
        status: 'Partially Satisfied',
        evaluator_type: 'semantic_ai',
        confidence_level: 'High',
      }),
      finding({
        id: 'semantic-2',
        status: 'Not Satisfied',
        evaluator_type: 'semantic_ai',
        confidence_level: 'Medium',
      }),
    ])

    expect(
      screen.getAllByText(
        'Results use confirmed evidence, rule-based checks, and semantic analysis when needed. The complete methodology is available in Methodology & Help.',
      ),
    ).toHaveLength(1)
    expect(
      screen.getByRole('link', {
        name: 'How does the platform determine results?',
      }),
    ).toHaveAttribute('href', '/evaluation-scope#evaluation-methods')
    expect(screen.queryByText('How was this result determined?'))
      .not.toBeInTheDocument()
    expect(screen.queryByText('Evidence reliability')).not.toBeInTheDocument()
    expect(screen.queryByText(/Evidence count/)).not.toBeInTheDocument()
    expect(container).not.toHaveTextContent('semantic_ai')
  })

  it('retains only directly explanatory marks and materials evidence', () => {
    renderSection([
      finding({
        id: 'marks',
        rule_id: 'RULE018',
        dimension: 'Marks and Totals',
        status: 'Not Satisfied',
        requirement_name: 'Marks action',
        evidence: [
          {
            id: 'declared',
            source_document: 'exam',
            evidence_type: 'declared_total',
            page_number: 1,
            item_reference: '40',
          },
          {
            id: 'marks-question',
            source_document: 'exam',
            evidence_type: 'question_text',
            page_number: 2,
            item_reference: 'Q2',
          },
        ],
      }),
      finding({
        id: 'materials',
        rule_id: 'RULE014',
        dimension: 'Supporting Materials',
        status: 'Not Verified',
        requirement_name: 'Materials action',
        evidence: [
          {
            id: 'figure-reference',
            source_document: 'exam',
            evidence_type: 'explicit_reference',
            page_number: 4,
            item_reference: 'Figure 5',
          },
          {
            id: 'unrelated-question',
            source_document: 'exam',
            evidence_type: 'question_text',
            page_number: 4,
            item_reference: 'Q4',
          },
        ],
      }),
    ])

    const disclosures = screen.getAllByText('View direct evidence')
    expect(disclosures).toHaveLength(2)
    fireEvent.click(disclosures[0])
    expect(screen.getByText('Declared total marks:', { exact: false }))
      .toBeInTheDocument()
    expect(
      within(disclosures[0].closest('details')!).queryByText('Q2'),
    ).not.toBeInTheDocument()
    fireEvent.click(disclosures[1])
    expect(screen.getByText('Figure 5')).toBeInTheDocument()
    expect(
      within(disclosures[1].closest('details')!).queryByText('Q4'),
    ).not.toBeInTheDocument()
  })

  it('hides a satisfied assessment-method check and keeps a non-satisfied one', () => {
    renderSection([
      finding({
        id: 'assessment-ok',
        rule_id: 'RULE003',
        requirement_id: 'REQ003',
        dimension: 'Assessment Alignment',
        requirement_name: 'Satisfied assessment check',
        status: 'Satisfied',
      }),
      finding({
        id: 'assessment-attention',
        rule_id: 'RULE003',
        requirement_id: 'REQ003',
        dimension: 'Assessment Alignment',
        requirement_name: 'Assessment method requires review',
        status: 'Not Satisfied',
      }),
    ])

    expect(screen.queryByText('Satisfied assessment check')).not.toBeInTheDocument()
    expect(screen.getByText('Assessment method requires review')).toBeInTheDocument()
  })

  it('uses approved Arabic wording and RTL without raw evidence or determination labels', () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    renderSection(
      [
        finding({
          status: 'Not Satisfied',
          evidence: [
            {
              id: 'raw-question',
              source_document: 'exam',
              evidence_type: 'question_text',
              page_number: 1,
              item_reference: 'Q1',
            },
          ],
        }),
      ],
      [],
      true,
    )

    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(screen.getByText('أثرها على النتيجة', { exact: false }))
      .toBeInTheDocument()
    expect(
      screen.getByText(
        'تعتمد النتائج على الأدلة المؤكدة والفحوصات القائمة على القواعد والتحليل الدلالي عند الحاجة. يمكن الاطلاع على المنهجية الكاملة من صفحة المنهجية والمساعدة.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'كيف تحسب المنصة النتائج؟' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('عدد الأدلة')).not.toBeInTheDocument()
    expect(screen.queryByText('كيف حُدّدت النتيجة؟')).not.toBeInTheDocument()
    expect(screen.queryByText('Evidence count')).not.toBeInTheDocument()
  })

  it('keeps findings visible while recommendation records are unavailable', () => {
    render(
      <MemoryRouter>
        <FindingsRecommendationsSection
          findings={[finding({})]}
          recommendations={{
            status: 'error',
            message: 'Recommendations unavailable.',
          }}
          recommendationsByFinding={new Map()}
          lookups={LOOKUPS}
          onRetryRecommendations={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText('Question-to-CLO Mapping')).toBeInTheDocument()
    expect(screen.getByText(/recommendations unavailable/i)).toBeInTheDocument()
  })
})
