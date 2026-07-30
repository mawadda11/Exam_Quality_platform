import { describe, expect, it } from 'vitest'
import { ARABIC_MESSAGES } from './I18nProvider'

describe('faculty Arabic terminology', () => {
  it.each([
    ['Overview', 'نظرة عامة'],
    ['Questions', 'الأسئلة'],
    ['Alignment & Coverage', 'المواءمة والتغطية'],
    ['Marks & Structure', 'الدرجات والبنية'],
    ['Materials & References', 'المواد والإحالات'],
    ['Findings & Recommendations', 'النتائج والتوصيات'],
    ['Report', 'التقرير'],
    ['Methodology & Help', 'المنهجية والمساعدة'],
    ['Reason for the result', 'سبب النتيجة'],
    ['Recommendation', 'التوصية'],
    ['Score impact', 'أثرها على النتيجة'],
    ['Evidence count', 'عدد الأدلة'],
    ['View evidence', 'عرض الأدلة'],
    ['How was this result determined?', 'كيف حُدّدت النتيجة؟'],
    ['Evidence reliability', 'موثوقية الأدلة'],
    ['Suggested relationship', 'ارتباط مقترح'],
    ['Original document excerpt', 'النص الأصلي من المستند'],
    ['Rule-based automated check', 'فحص آلي وفق قواعد محددة'],
    ['Semantic content analysis', 'تحليل دلالي لمحتوى السؤال'],
    ['Official Course Specification record', 'سجل رسمي من توصيف المقرر'],
    ['Suggested CLO', 'ناتج التعلم المقترح'],
    ['Suggested Course Topic', 'موضوع المقرر المقترح'],
    ['Alignment status', 'حالة المواءمة'],
    ['Short reason', 'سبب مختصر'],
    ['View mapping details', 'عرض تفاصيل الربط'],
    ['Supported', 'مدعوم'],
    ['Partially supported', 'مدعوم جزئيًا'],
    ['No supported relationship found', 'لم يظهر ارتباط واضح'],
    ['Coverage status', 'حالة التغطية'],
    ['Related questions', 'الأسئلة المرتبطة'],
    ['Assessment Method Consistency', 'اتساق طريقة التقييم'],
    ['Course Topic', 'موضوع المقرر'],
    ['Course Specification', 'توصيف المقرر'],
    ['Upload Course Specification', 'رفع توصيف المقرر'],
    ['Course Specification file', 'ملف توصيف المقرر'],
    [
      'Upload the completed official Course Specification PDF, such as a completed TP-153 template.',
      'ارفع ملف توصيف المقرر المعتمد بصيغة PDF، مثل نموذج TP-153 بعد تعبئته.',
    ],
    [
      'How does the platform determine results?',
      'كيف تحسب المنصة النتائج؟',
    ],
  ])('uses the approved translation for %s', (key, expected) => {
    expect(ARABIC_MESSAGES[key]).toBe(expected)
  })

  it('has Arabic catalog entries for the refined faculty flows', () => {
    const keys = [
      'The available checks use the confirmed evidence.',
      'The analyzer identifies source records and their document locations for review.',
      'Evidence disclosures preserve traceability without interrupting the primary faculty view.',
      'Extracted text',
      'Include',
      'View details in Alignment & Coverage',
      'View details in Marks & Structure',
      'View details in Materials & References',
    ]

    for (const key of keys) {
      expect(ARABIC_MESSAGES[key]).toMatch(/[\u0600-\u06ff]/)
    }
  })
})
