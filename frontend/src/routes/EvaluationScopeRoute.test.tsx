import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('presents supported, limited, and planned checks as platform scope rather than exam results', () => {
    renderRoute()

    expect(screen.getByRole('heading', { level: 1, name: 'Methodology & Help' }))
      .toBeInTheDocument()
    expect(screen.getByText('17')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Available checks' }))
      .toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Planned capabilities' }))
      .toBeInTheDocument()
    expect(screen.getByText(/planned checks are not treated as exam failures/i))
      .toBeInTheDocument()
    expect(screen.queryByText(/RULE\d{3}/)).not.toBeInTheDocument()
    expect(screen.queryByText(/v1\.0\.0|release/i)).not.toBeInTheDocument()
  })

  it('provides every approved methodology section through stable anchors', () => {
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

  it('focuses a linked methodology heading and supports Arabic RTL', async () => {
    window.localStorage.setItem('exam-quality-analyzer-locale', 'ar')
    renderRoute('/evaluation-scope#overall-score')

    await waitFor(() => expect(document.getElementById('overall-score')).toHaveFocus())
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(
      screen.getByRole('heading', { level: 1, name: 'المنهجية والمساعدة' }),
    ).toBeInTheDocument()
    expect(screen.queryByText(/تعذر عرض النص المترجم/)).not.toBeInTheDocument()
  })

  it('moves focus to a methodology section from the on-page navigation', async () => {
    renderRoute()

    fireEvent.click(screen.getByRole('link', { name: 'Overall score' }))
    await waitFor(() => expect(document.getElementById('overall-score')).toHaveFocus())
  })
})
