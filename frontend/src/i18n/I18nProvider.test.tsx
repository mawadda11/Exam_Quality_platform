import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { I18nProvider, useI18n } from './I18nProvider'

function LocaleProbe() {
  const { locale, setLocale, t } = useI18n()
  return (
    <>
      <span>{locale}</span>
      <span>{t('Exam Quality Analyzer')}</span>
      <button type="button" onClick={() => setLocale('en')}>English</button>
    </>
  )
}

describe('I18nProvider', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.lang = 'en'
    document.documentElement.dir = 'ltr'
  })

  it('defaults anonymous sessions to Arabic and applies document metadata', () => {
    render(<I18nProvider><LocaleProbe /></I18nProvider>)

    expect(screen.getByText('ar')).toBeInTheDocument()
    expect(screen.getByText('محلل جودة الاختبارات')).toBeInTheDocument()
    expect(document.documentElement).toHaveAttribute('lang', 'ar')
    expect(document.documentElement).toHaveAttribute('dir', 'rtl')
    expect(document.title).toBe('محلل جودة الاختبارات')
  })

  it('persists an explicit English selection and switches direction', () => {
    render(<I18nProvider><LocaleProbe /></I18nProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'English' }))

    expect(screen.getByText('en')).toBeInTheDocument()
    expect(screen.getByText('Exam Quality Analyzer')).toBeInTheDocument()
    expect(document.documentElement).toHaveAttribute('dir', 'ltr')
    expect(window.localStorage.getItem('exam-quality-analyzer-locale')).toBe('en')
  })
})
