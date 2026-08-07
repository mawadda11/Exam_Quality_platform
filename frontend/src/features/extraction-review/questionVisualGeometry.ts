import type {
  ExtractionReviewQuestion,
  ExtractionReviewQuestionBlank,
  ExtractionReviewQuestionOption,
  ExtractionReviewQuestionSourceSpan,
  ExtractionReviewSupportingMaterial,
} from '../../types/api'

export function unionGeometry(
  geometries: Array<ExtractionReviewQuestion['geometry']>,
): ExtractionReviewQuestion['geometry'] {
  const available = geometries.filter(
    (geometry): geometry is NonNullable<ExtractionReviewQuestion['geometry']> =>
      geometry !== null,
  )
  if (!available.length) return null
  return {
    x0: Math.min(...available.map((geometry) => geometry.x0)),
    top: Math.min(...available.map((geometry) => geometry.top)),
    x1: Math.max(...available.map((geometry) => geometry.x1)),
    bottom: Math.max(...available.map((geometry) => geometry.bottom)),
  }
}

export function visualGeometryForQuestion(
  item: ExtractionReviewQuestion,
  questions: ExtractionReviewQuestion[],
  options: ExtractionReviewQuestionOption[],
  blanks: ExtractionReviewQuestionBlank[],
  sourceSpans: ExtractionReviewQuestionSourceSpan[],
  materials: ExtractionReviewSupportingMaterial[],
): ExtractionReviewQuestion['geometry'] {
  if (
    item.geometry &&
    (item.extraction_method === 'manual_review' || item.extraction_method === 'review_adjusted')
  ) {
    return item.geometry
  }

  const combined = unionGeometry([
    item.geometry,
    ...options
      .filter((option) => option.question_source_record_id === item.source_record_id)
      .map((option) => option.geometry),
    ...blanks
      .filter((blank) => blank.question_source_record_id === item.source_record_id)
      .map((blank) => blank.geometry),
    ...sourceSpans
      .filter(
        (span) =>
          span.question_source_record_id === item.source_record_id &&
          span.option_source_record_id === null &&
          span.page_number === item.page_number,
      )
      .map((span) => span.geometry),
    ...materials
      .filter(
        (material) =>
          material.question_source_record_id === item.source_record_id &&
          material.page_number === item.page_number,
      )
      .map((material) => material.geometry),
  ])
  if (!combined) return null

  // The question's own stem geometry is the reliable vertical anchor. A noisy
  // source span or duplicated option must never move the crop above the stem.
  const anchorTop = item.geometry?.top ?? combined.top
  const nextTop = questions
    .filter(
      (candidate) =>
        candidate.source_record_id !== item.source_record_id &&
        candidate.page_number === item.page_number &&
        candidate.geometry !== null &&
        candidate.geometry.top > anchorTop + 4,
    )
    .map((candidate) => candidate.geometry?.top ?? Number.POSITIVE_INFINITY)
    .sort((left, right) => left - right)[0]

  const candidateBottom = Math.max(item.geometry?.bottom ?? combined.bottom, combined.bottom)
  const boundedBottom = Number.isFinite(nextTop)
    ? Math.max(anchorTop + 8, Math.min(candidateBottom, nextTop - 4))
    : candidateBottom + 12

  return {
    x0: Math.max(0, combined.x0 - 8),
    top: Math.max(0, anchorTop - 6),
    x1: combined.x1 + 8,
    bottom: boundedBottom,
  }
}
