import type { FindingEvidenceRef, QuestionResponse } from '../../types/api'

const ARABIC_DIGITS = new Map([
  ['٠', '0'],
  ['١', '1'],
  ['٢', '2'],
  ['٣', '3'],
  ['٤', '4'],
  ['٥', '5'],
  ['٦', '6'],
  ['٧', '7'],
  ['٨', '8'],
  ['٩', '9'],
  ['۰', '0'],
  ['۱', '1'],
  ['۲', '2'],
  ['۳', '3'],
  ['۴', '4'],
  ['۵', '5'],
  ['۶', '6'],
  ['۷', '7'],
  ['۸', '8'],
  ['۹', '9'],
])

function normalizeDigits(value: string): string {
  return [...value].map((character) => ARABIC_DIGITS.get(character) ?? character).join('')
}

function referenceParts(value: string): Array<number | string> {
  const normalized = normalizeDigits(value)
    .toLocaleLowerCase()
    .replace(/^(?:question|q|السؤال|سؤال|س)\s*/u, '')
  const parts = normalized.match(/\d+|\p{L}+/gu) ?? []
  return parts.map((part) => (/^\d+$/.test(part) ? Number(part) : part))
}

export function compareNaturalQuestionReferences(
  left: string,
  right: string,
): number {
  const leftParts = referenceParts(left)
  const rightParts = referenceParts(right)
  const length = Math.max(leftParts.length, rightParts.length)

  for (let index = 0; index < length; index += 1) {
    const leftPart = leftParts[index]
    const rightPart = rightParts[index]
    if (leftPart === undefined) return -1
    if (rightPart === undefined) return 1
    if (leftPart === rightPart) continue
    if (typeof leftPart === 'number' && typeof rightPart === 'number') {
      return leftPart - rightPart
    }
    if (typeof leftPart === 'number') return -1
    if (typeof rightPart === 'number') return 1
    const compared = leftPart.localeCompare(rightPart, ['ar', 'en'], {
      numeric: true,
      sensitivity: 'base',
    })
    if (compared !== 0) return compared
  }

  return normalizeDigits(left).localeCompare(normalizeDigits(right), ['ar', 'en'], {
    numeric: true,
    sensitivity: 'base',
  })
}

function isParentOf(
  parent: QuestionResponse,
  child: QuestionResponse,
): boolean {
  return child.parent_question_id === parent.id
}

export function compareQuestionRecords(
  left: QuestionResponse,
  right: QuestionResponse,
): number {
  if (isParentOf(left, right)) return -1
  if (isParentOf(right, left)) return 1

  const leftHasSequence = Number.isFinite(left.sequence) && left.sequence > 0
  const rightHasSequence = Number.isFinite(right.sequence) && right.sequence > 0
  if (leftHasSequence && rightHasSequence && left.sequence !== right.sequence) {
    return left.sequence - right.sequence
  }
  if (leftHasSequence !== rightHasSequence) return leftHasSequence ? -1 : 1

  if (left.page_number !== right.page_number) {
    return left.page_number - right.page_number
  }
  const referenceOrder = compareNaturalQuestionReferences(
    left.number_label,
    right.number_label,
  )
  if (referenceOrder !== 0) return referenceOrder
  return left.id.localeCompare(right.id)
}

export function sortQuestionsForFaculty(
  questions: QuestionResponse[],
): QuestionResponse[] {
  return [...questions].sort(compareQuestionRecords)
}

export function independentlyScorableQuestions(
  questions: QuestionResponse[],
): QuestionResponse[] {
  const structuralParentIds = new Set(
    questions
      .map((question) => question.parent_question_id)
      .filter((id): id is string => id !== null),
  )
  return questions.filter((question) => !structuralParentIds.has(question.id))
}

export function sortQuestionReferences(
  references: string[],
  questions: QuestionResponse[],
  pageByReference: ReadonlyMap<string, number> = new Map(),
): string[] {
  const unique = [...new Set(references)]
  const orderedQuestions = sortQuestionsForFaculty(questions)
  const sourceOrder = new Map(
    orderedQuestions.map((question, index) => [question.number_label, index]),
  )
  const stableOrder = new Map(unique.map((reference, index) => [reference, index]))

  return unique.sort((left, right) => {
    const leftSourceOrder = sourceOrder.get(left)
    const rightSourceOrder = sourceOrder.get(right)
    if (leftSourceOrder !== undefined && rightSourceOrder !== undefined) {
      return leftSourceOrder - rightSourceOrder
    }
    if (leftSourceOrder !== undefined) return -1
    if (rightSourceOrder !== undefined) return 1

    const leftPage = pageByReference.get(left)
    const rightPage = pageByReference.get(right)
    if (leftPage !== undefined && rightPage !== undefined && leftPage !== rightPage) {
      return leftPage - rightPage
    }
    if (leftPage !== undefined) return -1
    if (rightPage !== undefined) return 1

    const referenceOrder = compareNaturalQuestionReferences(left, right)
    if (referenceOrder !== 0) return referenceOrder
    return (stableOrder.get(left) ?? 0) - (stableOrder.get(right) ?? 0)
  })
}

export function sortEvidenceReferences(
  evidence: FindingEvidenceRef[],
  questions: QuestionResponse[],
): FindingEvidenceRef[] {
  const sourceOrder = new Map(
    sortQuestionsForFaculty(questions).map((question, index) => [
      question.number_label,
      index,
    ]),
  )
  return [...evidence].sort((left, right) => {
    const leftOrder = sourceOrder.get(left.item_reference)
    const rightOrder = sourceOrder.get(right.item_reference)
    if (leftOrder !== undefined && rightOrder !== undefined) return leftOrder - rightOrder
    if (leftOrder !== undefined) return -1
    if (rightOrder !== undefined) return 1
    if (left.page_number !== right.page_number) return left.page_number - right.page_number
    const referenceOrder = compareNaturalQuestionReferences(
      left.item_reference,
      right.item_reference,
    )
    return referenceOrder || left.id.localeCompare(right.id)
  })
}

export function compareNaturalCloIdentifiers(left: string, right: string): number {
  return compareNaturalQuestionReferences(
    left.replace(/^CLO/i, 'Q'),
    right.replace(/^CLO/i, 'Q'),
  )
}
