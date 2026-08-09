import { describe, expect, it } from 'vitest'
import type { FindingResponse, RecommendationResponse } from '../types/api'
import {
  presentFindingExplanation,
  presentRecommendation,
  presentRequirementName,
} from './governedPresentation'

const FINDING = {
  requirement_id: 'REQ001',
  requirement_name: 'Question-to-CLO Mapping',
  status: 'Satisfied',
  explanation: 'Original governed explanation.',
} as FindingResponse

const RECOMMENDATION = {
  recommendation_id: 'REC001',
  title: 'Map the Question to a CLO',
  text: 'Original governed recommendation.',
  target_user: 'Faculty and Course Coordinator',
  recommendation_type: 'Corrective',
} as RecommendationResponse

describe('governed presentation localization', () => {
  it('uses stable identifiers for Arabic presentation without replacing English source wording', () => {
    expect(presentRequirementName('REQ001', FINDING.requirement_name, 'ar'))
      .toBe('ربط السؤال بناتج التعلم للمقرر')
    expect(presentFindingExplanation(FINDING, 'ar')).toBe(FINDING.explanation)
    expect(presentFindingExplanation(FINDING, 'en')).toBe(FINDING.explanation)

    const arabic = presentRecommendation(RECOMMENDATION, 'ar')
    expect(arabic.title).toBe('راجع علاقة السؤال بناتج التعلم')
    expect(arabic.text).toContain('فقط عندما تدعمها الأدلة المؤكدة')
    expect(arabic.targetUser).toBe('عضو هيئة التدريس ومنسق المقرر')
    const english = presentRecommendation(RECOMMENDATION, 'en')
    expect(english.title).toBe('Review the question-to-CLO relationship')
    expect(english.text).toContain('otherwise leave it unassigned')
    expect(RECOMMENDATION.text).toBe('Original governed recommendation.')
  })

  it('uses Course Specification terminology in presentation without mutating source records', () => {
    const source = {
      ...FINDING,
      explanation: 'No CLOs were extracted from the TP-153.',
    } as FindingResponse
    const recommendation = {
      ...RECOMMENDATION,
      recommendation_id: 'REC999',
      text: 'Complete the populated TP-153 before continuing.',
    } as RecommendationResponse

    expect(presentFindingExplanation(source, 'en'))
      .toBe('No CLOs were extracted from the Course Specification.')
    expect(presentRecommendation(recommendation, 'en').text)
      .toBe('Complete the populated Course Specification before continuing.')
    expect(source.explanation).toContain('TP-153')
    expect(recommendation.text).toContain('TP-153')
  })

  it('uses balanced evidence-first wording for unsupported questions', () => {
    const unsupported = {
      ...RECOMMENDATION,
      recommendation_id: 'REC007',
    } as RecommendationResponse

    expect(presentRecommendation(unsupported, 'en').text).toBe(
      'Verify the approved course specification. If the topic is officially included but missing from the uploaded specification, update the specification. Otherwise, review or replace the question.',
    )
    expect(presentRecommendation(unsupported, 'ar').text).toBe(
      'تحقّق من توصيف المقرر المعتمد. إذا كان الموضوع معتمدًا لكنه غير مدرج في الملف المرفوع، فحدّث التوصيف؛ وإلا فراجع السؤال أو استبدله.',
    )
  })
})
