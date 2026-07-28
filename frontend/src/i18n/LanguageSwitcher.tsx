import { useState } from 'react'
import { updateFacultyPreferences } from '../api/auth'
import { useOptionalAuth } from '../features/auth/AuthProvider'
import type { Locale } from '../types/api'
import { useI18n } from './I18nProvider'

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n()
  const auth = useOptionalAuth()
  const [isSaving, setIsSaving] = useState(false)

  async function changeLocale(nextLocale: Locale): Promise<void> {
    if (nextLocale === locale || isSaving) return
    setLocale(nextLocale)
    if (auth?.status !== 'authenticated') return

    setIsSaving(true)
    try {
      await updateFacultyPreferences(nextLocale)
    } catch {
      // The local preference remains available even when remote persistence fails.
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="language-switcher" role="group" aria-label={t('Interface language')}>
      <button
        type="button"
        className={`language-switcher__button${locale === 'ar' ? ' is-active' : ''}`}
        aria-pressed={locale === 'ar'}
        disabled={isSaving}
        onClick={() => void changeLocale('ar')}
      >
        {locale === 'ar' ? 'العربية' : 'Arabic'}
      </button>
      <button
        type="button"
        className={`language-switcher__button${locale === 'en' ? ' is-active' : ''}`}
        aria-pressed={locale === 'en'}
        disabled={isSaving}
        onClick={() => void changeLocale('en')}
      >
        {locale === 'ar' ? 'الإنجليزية' : 'English'}
      </button>
    </div>
  )
}
