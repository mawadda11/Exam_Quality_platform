import { describe, expect, it } from 'vitest'
import type { ExtractionReviewQuestion } from '../../types/api'
import { visualGeometryForQuestion } from './questionVisualGeometry'

function question(
  id: string,
  top: number,
  bottom: number,
  method = 'direct_text',
): ExtractionReviewQuestion {
  return {
    source_record_id: id,
    included: true,
    parent_source_record_id: null,
    number_label: id,
    question_text: id,
    page_number: 1,
    marks: null,
    sequence: Number(id.replace(/\D/g, '')),
    extraction_confidence: 1,
    geometry: { x0: 50, top, x1: 300, bottom },
    question_type: 'short_answer',
    instructions: null,
    extraction_method: method,
    review_status: 'reviewed',
  }
}

describe('visual question geometry', () => {
  it('caps a noisy candidate before the next question', () => {
    const q1 = question('Q1', 100, 120)
    const q2 = question('Q2', 200, 220)
    const geometry = visualGeometryForQuestion(
      q1,
      [q1, q2],
      [],
      [],
      [
        {
          source_record_id: 'span-1',
          question_source_record_id: 'Q1',
          option_source_record_id: null,
          provider: 'pdfplumber',
          provider_version: null,
          source_line_id: 'P1-N1',
          original_text: 'noisy page-wide source span',
          page_number: 1,
          geometry: { x0: 20, top: 40, x1: 500, bottom: 350 },
          extraction_confidence: 1,
          extraction_method: 'direct_text',
        },
      ],
      [],
    )

    expect(geometry?.top).toBe(94)
    expect(geometry?.bottom).toBe(196)
  })

  it('uses an explicitly adjusted manual region exactly', () => {
    const manual = question('Q1', 80, 240, 'manual_review')

    expect(visualGeometryForQuestion(manual, [manual], [], [], [], [])).toEqual(
      manual.geometry,
    )
  })
})
