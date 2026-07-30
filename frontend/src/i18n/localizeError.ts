import { ApiError } from '../api/client'
import type { Locale } from '../types/api'
import { ARABIC_MESSAGES } from './I18nProvider'

type Translate = (key: string, variables?: Record<string, string | number>) => string

function presentServerTerminology(message: string): string {
  return message
    .replaceAll('TP-153 Course Specification', 'Course Specification')
    .replaceAll('TP-153', 'Course Specification')
}

export function localizeInterfaceError(
  error: unknown,
  locale: Locale,
  t: Translate,
  fallbackKey: string,
): string {
  if (locale === 'en' && error instanceof ApiError) {
    return presentServerTerminology(error.detail)
  }
  if (locale === 'ar' && error instanceof ApiError) {
    const presented = presentServerTerminology(error.detail)
    return (
      ARABIC_MESSAGES[presented] ??
      ARABIC_MESSAGES[error.detail] ??
      t(fallbackKey)
    )
  }
  return t(fallbackKey)
}

export function localizeServerMessage(
  message: string | null | undefined,
  locale: Locale,
  t: Translate,
  fallbackKey: string,
): string {
  if (!message) return t(fallbackKey)
  const presented = presentServerTerminology(message)
  if (locale === 'en') return presented
  return ARABIC_MESSAGES[presented] ?? ARABIC_MESSAGES[message] ?? t(fallbackKey)
}
