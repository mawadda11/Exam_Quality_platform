import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { localizeInterfaceError, localizeServerMessage } from './localizeError'

describe('workflow error presentation terminology', () => {
  const t = vi.fn((key: string) => key)

  it('presents legacy backend identifiers as Course Specification in English', () => {
    const detail =
      'The original examination and TP-153 files are required before retrying.'
    expect(localizeInterfaceError(new ApiError(409, detail), 'en', t, 'Fallback'))
      .toBe(
        'The original examination and Course Specification files are required before retrying.',
      )
    expect(
      localizeServerMessage(
        'The TP-153 Course Specification could not be extracted. Review the PDF and retry.',
        'en',
        t,
        'Fallback',
      ),
    ).toBe(
      'The Course Specification could not be extracted. Review the PDF and retry.',
    )
  })

  it('uses the approved Arabic workflow wording after presentation normalization', () => {
    expect(
      localizeServerMessage(
        'The original examination and TP-153 files are required before retrying.',
        'ar',
        t,
        'Fallback',
      ),
    ).toBe(
      'يلزم توفر ملف الاختبار وتوصيف المقرر الأصليين قبل إعادة المحاولة.',
    )
  })
})
