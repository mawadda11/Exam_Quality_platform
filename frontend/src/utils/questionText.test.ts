import { describe, expect, it } from 'vitest'
import { displayQuestionText } from './questionText'

describe('displayQuestionText', () => {
  it('removes a duplicated question label even when PDF spacing differs', () => {
    expect(
      displayQuestionText(
        'Q 1.1 ما رمز حالة HTTP الذي يشير عادةً إلى أن المورد غير موجود؟',
        'Q1.1',
      ),
    ).toBe('ما رمز حالة HTTP الذي يشير عادةً إلى أن المورد غير موجود؟')
  })

  it('handles spaced parenthesized labels without rewriting mixed Arabic-English text', () => {
    expect(
      displayQuestionText(
        'Q 3 (a) اشرح باختصار نموذج Client-Server، واذكر دور بروتوكول HTTP.',
        'Q3(a)',
      ),
    ).toBe('اشرح باختصار نموذج Client-Server، واذكر دور بروتوكول HTTP.')
  })

  it('leaves text unchanged when the leading text is not the same question label', () => {
    expect(displayQuestionText('Q10 Explain HTTP.', 'Q1')).toBe('Q10 Explain HTTP.')
  })

  it('leaves already-clean Arabic mixed text unchanged', () => {
    const text = 'استخدام HTTPS يعني أن المستخدم أصبح مجهول الهوية تلقائيًا.'
    expect(displayQuestionText(text, 'Q2.1')).toBe(text)
  })
})
