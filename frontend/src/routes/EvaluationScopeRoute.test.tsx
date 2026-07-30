import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { EvaluationScopeRoute } from './EvaluationScopeRoute'

describe('EvaluationScopeRoute', () => {
  beforeEach(() => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'en')
  })

  function renderRoute(initialEntry = '/evaluation-scope') {
    return render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <I18nProvider>
          <EvaluationScopeRoute />
        </I18nProvider>
      </MemoryRouter>,
    )
  }

  it('uses the current brand and a compact eight-link guide hierarchy', () => {
    const { container } = renderRoute()

    expect(
      screen.getByRole('heading', { level: 1, name: 'Methodology & Help' }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/what the Exam Quality Analyzer evaluates/i),
    ).toBeInTheDocument()

    const navigation = screen.getByRole('navigation', {
      name: 'Quick navigation',
    })
    expect(within(navigation).getAllByRole('link')).toHaveLength(8)
    expect(
      within(navigation).getByRole('link', { name: 'Evaluation model' }),
    ).toHaveAttribute('href', '#evaluation-model')
    expect(
      within(navigation).getByRole('link', { name: 'FAQ' }),
    ).toHaveAttribute('href', '#frequently-asked-questions')

    const pageText = container.textContent ?? ''
    expect(pageText).not.toMatch(/\bAI\b|Artificial Intelligence/i)
    expect(pageText).not.toMatch(/simulated processing|functional prototype|demo-only/i)
    expect(pageText).not.toMatch(/Question Type Classification/i)
  })

  it('presents five accessible statuses and the authoritative scoring policy', () => {
    renderRoute()

    const statusSection = screen.getByRole('region', {
      name: 'Evaluation Status Model',
    })
    for (const status of [
      'Satisfied',
      'Partially Satisfied',
      'Not Satisfied',
      'Not Verified',
      'Not Applicable',
    ]) {
      expect(within(statusSection).getByText(status)).toBeInTheDocument()
    }
    expect(
      within(statusSection).getAllByTestId('methodology-status-card'),
    ).toHaveLength(5)

    const scoringSection = screen.getByRole('region', {
      name: 'Scoring Policy',
    })
    expect(
      within(scoringSection).getByLabelText(
        'Overall Score equals the sum of scored status values divided by the number of verified and applicable results, multiplied by 100.',
      ),
    ).toBeInTheDocument()
    expect(
      within(scoringSection).getByText(/Satisfied.*1\.0/i),
    ).toBeInTheDocument()
    expect(
      within(scoringSection).getByText(/Partially Satisfied.*0\.5/i),
    ).toBeInTheDocument()
    expect(
      within(scoringSection).getByText(/Not Satisfied.*0\.0/i),
    ).toBeInTheDocument()
    expect(
      within(scoringSection).getByText(/The score is shown as Insufficient Evidence/i),
    ).toBeInTheDocument()
    expect(
      within(scoringSection).getByText(/no rule weights, dimension weights, severity weights, or readiness bands/i),
    ).toBeInTheDocument()
  })

  it('shows the real nine-step workflow without outdated processing language', () => {
    renderRoute()

    const workflow = screen.getByRole('region', { name: 'Analysis Workflow' })
    expect(within(workflow).getAllByRole('listitem')).toHaveLength(8)
    expect(
      within(workflow).getByText('Enter the analysis information.'),
    ).toBeInTheDocument()
    expect(
      within(workflow).getByText('Confirm or correct extracted evidence.'),
    ).toBeInTheDocument()
    expect(
      within(workflow).getByText('Preview or download the report.'),
    ).toBeInTheDocument()
    expect(within(workflow).queryByText(/simulated|12 stages|demo/i))
      .not.toBeInTheDocument()
  })

  it('keeps governed scope counts derived and presents planned checks as non-scoring', () => {
    renderRoute()

    const checksSection = screen.getByRole('region', {
      name: 'What the analyzer evaluates',
    })
    const summary = within(checksSection).getByLabelText(
      'Current evaluation scope summary',
    )
    expect(within(summary).getByText('17')).toBeInTheDocument()
    expect(within(summary).getByText('1')).toBeInTheDocument()
    expect(within(summary).getByText('3')).toBeInTheDocument()
    expect(
      within(checksSection).getByText('CLO and topic relationships'),
    ).toBeInTheDocument()
    expect(
      within(checksSection).getByText('Materials and references'),
    ).toBeInTheDocument()
    expect(
      within(checksSection).getAllByText('Planned, not scored'),
    ).toHaveLength(3)
    expect(within(checksSection).queryByText(/RULE\d{3}/))
      .not.toBeInTheDocument()
    expect(within(checksSection).queryByText(/failed|failure/i))
      .not.toBeInTheDocument()
  })

  it('preserves evidence, document review, privacy, reports, and limitation guidance', () => {
    renderRoute()

    const governance = screen.getByRole('region', {
      name: 'Evidence and Governance Principles',
    })
    expect(within(governance).getAllByRole('listitem')).toHaveLength(12)
    expect(
      within(governance).getByText(
        'Original evidence remains preserved; corrections create traceable revisions.',
      ),
    ).toBeInTheDocument()

    const documents = screen.getByRole('region', {
      name: 'Required Documents and Extraction Review',
    })
    expect(within(documents).getByText('Exam PDF')).toBeInTheDocument()
    expect(
      within(documents).getByText('Populated Course Specification / TP-153'),
    ).toBeInTheDocument()
    expect(
      within(documents).getByText('Verify question marks.'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Analyses are private to the authenticated owner.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        'To evaluate a revised exam, create a New Analysis. Each analysis and its reports are evaluated and stored independently.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        'Planned capabilities are not counted as exam failures.',
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(/Use View mapping details/i)).toBeInTheDocument()
    expect(screen.queryByText(/View Comparison/i)).not.toBeInTheDocument()
  })

  it('uses a single-open accessible FAQ accordion', () => {
    renderRoute()

    const faq = screen.getByRole('region', {
      name: 'Frequently Asked Questions',
    })
    const buttons = within(faq).getAllByRole('button')
    expect(buttons).toHaveLength(9)
    expect(buttons[0]).toHaveAttribute('aria-expanded', 'true')
    expect(buttons[1]).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(buttons[1])

    expect(buttons[0]).toHaveAttribute('aria-expanded', 'false')
    expect(buttons[1]).toHaveAttribute('aria-expanded', 'true')
    expect(buttons[1]).toHaveAttribute(
      'aria-controls',
      'methodology-faq-panel-1',
    )
    expect(
      screen.getByRole('region', { name: 'Why is a rule excluded from the score?' }),
    ).toBeVisible()
  })

  it('preserves every established methodology deep-link anchor', () => {
    renderRoute()

    for (const anchor of [
      'what-we-evaluate',
      'required-documents',
      'analysis-workflow',
      'extraction-review',
      'evaluation-methods',
      'academic-statuses',
      'overall-score',
      'not-verified',
      'confidence',
      'evidence-traceability',
      'suggested-relationships',
      'local-privacy',
      'reports-reanalysis',
      'limitations',
      'frequently-asked-questions',
    ]) {
      expect(document.getElementById(anchor)).toBeInTheDocument()
    }
  })

  it('focuses linked sections and provides natural Arabic RTL content', async () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    const { container } = renderRoute('/evaluation-scope#overall-score')

    await waitFor(() =>
      expect(document.getElementById('overall-score')).toHaveFocus(),
    )
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'المنهجية والمساعدة',
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('navigation', { name: 'التنقل السريع' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'نموذج حالات التقييم' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'سياسة احتساب الدرجة' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'خطوات التحليل' }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('مستوفى جزئيًا')).not.toHaveLength(0)
    expect(container).toHaveTextContent('عرض تفاصيل الربط')
    expect(container).not.toHaveTextContent('تعذر عرض النص المترجم.')
  })

  it('moves focus from compact navigation to the selected section', async () => {
    renderRoute()

    fireEvent.click(screen.getByRole('link', { name: 'Scoring' }))
    await waitFor(() =>
      expect(document.getElementById('overall-score')).toHaveFocus(),
    )
  })
})
