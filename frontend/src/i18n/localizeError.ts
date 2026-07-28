import { ApiError } from '../api/client'
import type { Locale } from '../types/api'
import { ARABIC_MESSAGES } from './I18nProvider'

type Translate = (key: string, variables?: Record<string, string | number>) => string

export function localizeInterfaceError(
  error: unknown,
  locale: Locale,
  t: Translate,
  fallbackKey: string,
): string {
  if (locale === 'en' && error instanceof ApiError) return error.detail
  if (locale === 'ar' && error instanceof ApiError) {
    return ARABIC_MESSAGES[error.detail] ?? t(fallbackKey)
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
  if (locale === 'en') return message
  return ARABIC_MESSAGES[message] ?? t(fallbackKey)
}
