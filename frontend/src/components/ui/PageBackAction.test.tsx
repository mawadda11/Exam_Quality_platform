import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { I18nProvider } from '../../i18n/I18nProvider'
import { PageBackAction } from './PageBackAction'

function CurrentPath() {
  return <output>{useLocation().pathname}</output>
}

function renderAt(pathname: string, locale: 'ar' | 'en' = 'en') {
  window.localStorage.setItem('exam-quality-analyzer-locale', locale)
  return render(
    <I18nProvider>
      <MemoryRouter initialEntries={[pathname]}>
        <PageBackAction />
        <Routes>
          <Route path="*" element={<CurrentPath />} />
        </Routes>
      </MemoryRouter>
    </I18nProvider>,
  )
}

describe('PageBackAction', () => {
  beforeEach(() => {
    window.localStorage.clear()
    delete document.body.dataset.unsavedExtractionReview
  })

  it.each([
    ['/analyses', '/dashboard'],
    ['/analyses/new', '/analyses'],
    ['/analyses/a1/documents', '/analyses'],
    ['/analyses/a1/start', '/analyses/a1/documents'],
    ['/analyses/a1/review', '/analyses'],
    ['/analyses/a1/progress', '/analyses'],
    ['/analyses/a1/results/overview', '/analyses'],
    ['/reports', '/dashboard'],
    ['/reports/r1/preview', '/reports'],
    ['/evaluation-scope', '/dashboard'],
    ['/unknown', '/dashboard'],
  ])('uses an explicit destination from %s to %s', (pathname, destination) => {
    renderAt(pathname)
    expect(screen.getByRole('link', { name: 'Back' })).toHaveAttribute('href', destination)
  })

  it('uses visually correct LTR and RTL arrows', () => {
    const { unmount } = renderAt('/analyses', 'en')
    expect(screen.getByText('←')).toBeInTheDocument()
    unmount()
    renderAt('/analyses', 'ar')
    expect(screen.getByText('→')).toBeInTheDocument()
  })

  it('warns before discarding dirty extraction-review edits', () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderAt('/analyses/a1/review')
    document.body.dataset.unsavedExtractionReview = 'true'
    fireEvent.click(screen.getByRole('link', { name: 'Back' }))
    expect(confirm).toHaveBeenCalledOnce()
    expect(screen.getByText('/analyses/a1/review')).toBeInTheDocument()
  })
})
