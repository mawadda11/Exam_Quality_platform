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
    expect(presentFindingExplanation(FINDING, 'ar')).toContain('استيفاء هذا المتطلب')
    expect(presentFindingExplanation(FINDING, 'en')).toBe(FINDING.explanation)

    const arabic = presentRecommendation(RECOMMENDATION, 'ar')
    expect(arabic.title).toBe('اربط السؤال بناتج تعلم')
    expect(arabic.targetUser).toBe('عضو هيئة التدريس ومنسق المقرر')
    expect(presentRecommendation(RECOMMENDATION, 'en').text)
      .toBe(RECOMMENDATION.text)
  })
})
