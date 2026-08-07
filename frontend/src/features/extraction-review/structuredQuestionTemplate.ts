import type {
  ExtractionReviewEvidence,
  ExtractionReviewQuestion,
  ExtractionReviewQuestionOption,
  ExtractionReviewSnapshot,
  QuestionType,
} from '../../types/api'

export const STRUCTURED_QUESTION_TEMPLATE_HEADERS = [
  'question_number',
  'question_text',
  'marks',
  'question_type',
  'options',
] as const

const REQUIRED_HEADERS = ['question_number', 'question_text', 'marks'] as const
const SUPPORTED_TYPES = new Set<QuestionType>([
  'multiple_choice',
  'true_false',
  'fill_in_blank',
  'short_answer',
  'essay',
])

export interface StructuredQuestionRow {
  questionNumber: string
  questionText: string
  questionType: QuestionType
  marks: number | null
  pageNumber: number
  parentQuestionNumber: string | null
  options: Array<{ label: string; text: string }>
}

export class StructuredQuestionTemplateError extends Error {
  readonly rowNumber: number | null

  constructor(message: string, rowNumber: number | null = null) {
    super(message)
    this.name = 'StructuredQuestionTemplateError'
    this.rowNumber = rowNumber
  }
}

function parseCsvRecords(input: string): string[][] {
  const records: string[][] = []
  let record: string[] = []
  let field = ''
  let quoted = false

  for (let index = 0; index < input.length; index += 1) {
    const character = input[index]
    if (quoted) {
      if (character === '"') {
        if (input[index + 1] === '"') {
          field += '"'
          index += 1
        } else {
          quoted = false
        }
      } else {
        field += character
      }
      continue
    }

    if (character === '"') {
      quoted = true
    } else if (character === ',') {
      record.push(field)
      field = ''
    } else if (character === '\n' || character === '\r') {
      if (character === '\r' && input[index + 1] === '\n') index += 1
      record.push(field)
      field = ''
      if (record.some((value) => value.trim() !== '')) records.push(record)
      record = []
    } else {
      field += character
    }
  }

  if (quoted) {
    throw new StructuredQuestionTemplateError('The CSV contains an unclosed quoted field.')
  }
  record.push(field)
  if (record.some((value) => value.trim() !== '')) records.push(record)
  return records
}

function parseOptionalMarks(value: string, rowNumber: number): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) {
    throw new StructuredQuestionTemplateError('Marks must be empty or a non-negative number.', rowNumber)
  }
  return parsed
}

function parsePageNumber(value: string, rowNumber: number): number {
  if (!value.trim()) return 1
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed < 1) {
    throw new StructuredQuestionTemplateError('Page number must be a positive whole number.', rowNumber)
  }
  return parsed
}

function splitOptions(value: string): Array<{ label: string; text: string }> {
  return value
    .split('|')
    .map((text) => text.trim())
    .filter(Boolean)
    .map((text, index) => ({ label: String.fromCharCode(65 + index), text }))
}

function inferQuestionType(
  questionText: string,
  options: Array<{ label: string; text: string }>,
): QuestionType {
  if (options.length >= 2) return 'multiple_choice'
  const normalized = questionText.toLowerCase()
  if (
    /\b(?:true\s*(?:or|\/)\s*false|t\s*\/\s*f)\b/.test(normalized) ||
    /(?:صح\s*(?:أو|\/|و)\s*خطأ)/.test(questionText)
  ) {
    return 'true_false'
  }
  if (/_{3,}|\.{4,}|…{2,}/.test(questionText)) return 'fill_in_blank'
  return 'short_answer'
}

function parseQuestionType(
  value: string,
  questionText: string,
  options: Array<{ label: string; text: string }>,
  rowNumber: number,
): QuestionType {
  if (!value.trim()) return inferQuestionType(questionText, options)
  const questionType = value.trim() as QuestionType
  if (!SUPPORTED_TYPES.has(questionType)) {
    throw new StructuredQuestionTemplateError(
      'Question type must be multiple_choice, true_false, fill_in_blank, short_answer, or essay.',
      rowNumber,
    )
  }
  return questionType
}

function legacyOptions(
  record: string[],
  valueAt: (record: string[], header: string) => string,
): Array<{ label: string; text: string }> {
  return ['A', 'B', 'C', 'D']
    .map((label) => ({
      label,
      text: valueAt(record, `option_${label.toLowerCase()}`),
    }))
    .filter((option) => option.text.length > 0)
}

export function parseStructuredQuestionTemplate(input: string): StructuredQuestionRow[] {
  const records = parseCsvRecords(input.replace(/^\uFEFF/, ''))
  if (records.length < 2) {
    throw new StructuredQuestionTemplateError('The template must contain a header and at least one question row.')
  }

  const headers = records[0].map((value) => value.trim().toLowerCase())
  const missingHeaders = REQUIRED_HEADERS.filter((header) => !headers.includes(header))
  if (missingHeaders.length > 0) {
    throw new StructuredQuestionTemplateError(
      `Missing required columns: ${missingHeaders.join(', ')}.`,
    )
  }
  const column = new Map(headers.map((header, index) => [header, index]))
  const valueAt = (record: string[], header: string): string =>
    record[column.get(header) ?? -1]?.trim() ?? ''

  const rows = records.slice(1).map((record, index) => {
    const rowNumber = index + 2
    const questionNumber = valueAt(record, 'question_number')
    const questionText = valueAt(record, 'question_text')
    if (!questionNumber) {
      throw new StructuredQuestionTemplateError('Question number is required.', rowNumber)
    }
    if (!questionText) {
      throw new StructuredQuestionTemplateError('Question text is required.', rowNumber)
    }

    const compactOptions = splitOptions(valueAt(record, 'options'))
    const options = compactOptions.length > 0 ? compactOptions : legacyOptions(record, valueAt)
    const questionType = parseQuestionType(
      valueAt(record, 'question_type'),
      questionText,
      options,
      rowNumber,
    )

    if (questionType === 'multiple_choice' && options.length < 2) {
      throw new StructuredQuestionTemplateError(
        'A multiple-choice question needs at least two answer options.',
        rowNumber,
      )
    }
    if (questionType !== 'multiple_choice' && options.length > 0) {
      throw new StructuredQuestionTemplateError(
        'Answer-option columns must be empty unless the question type is multiple_choice.',
        rowNumber,
      )
    }

    return {
      questionNumber,
      questionText,
      questionType,
      marks: parseOptionalMarks(valueAt(record, 'marks'), rowNumber),
      pageNumber: parsePageNumber(valueAt(record, 'page_number'), rowNumber),
      parentQuestionNumber: valueAt(record, 'parent_question_number') || null,
      options,
    }
  })

  const duplicates = rows
    .map((row) => row.questionNumber)
    .filter((value, index, all) => all.indexOf(value) !== index)
  if (duplicates.length > 0) {
    throw new StructuredQuestionTemplateError(
      `Question numbers must be unique in the structured template: ${[...new Set(duplicates)].join(', ')}.`,
    )
  }
  const numbers = new Set(rows.map((row) => row.questionNumber))
  for (const [index, row] of rows.entries()) {
    if (row.parentQuestionNumber && !numbers.has(row.parentQuestionNumber)) {
      throw new StructuredQuestionTemplateError(
        `Parent question ${row.parentQuestionNumber} was not found in the template.`,
        index + 2,
      )
    }
  }
  return rows
}

const QUESTION_START = /^\s*(?:(?:Q(?:uestion)?|س)\s*)?(\d+(?:\s*\([a-zA-Z]\))?)\s*(.*)$/i
const QUESTION_PREFIX_MARKS = /^\(\s*(\d+(?:\.\d+)?)\s*(?:marks?)?\s*\)\s*[:._\-–—]*\s*(.*)$/i
const OPTION_START = /^\s*([A-D])\s*[.):\-–—]+\s*(.+)$/i
const EXPLICIT_MARKS = /\s*(?:\[|\()\s*(\d+(?:\.\d+)?)\s*(?:marks?|درجات?|علامات?)\s*(?:\]|\))\s*$/i
const SQUARE_MARKS = /\s*\[\s*(\d+(?:\.\d+)?)\s*\]\s*$/

function extractVisibleMarks(text: string): { text: string; marks: number | null } {
  const explicit = text.match(EXPLICIT_MARKS) ?? text.match(SQUARE_MARKS)
  if (!explicit) return { text: text.trim(), marks: null }
  return {
    text: text.slice(0, explicit.index).trimEnd(),
    marks: Number(explicit[1]),
  }
}

export function parsePastedQuestions(input: string): StructuredQuestionRow[] {
  const normalized = input.replace(/\r\n?/g, '\n').trim()
  if (!normalized) {
    throw new StructuredQuestionTemplateError('Paste at least one question before importing.')
  }

  const lines = normalized.split('\n')
  const rows: StructuredQuestionRow[] = []
  let current:
    | {
        number: string
        parts: string[]
        options: Array<{ label: string; text: string }>
        marks: number | null
      }
    | null = null

  const flush = (): void => {
    if (!current) return
    const questionText = current.parts.join(' ').replace(/\s+/g, ' ').trim()
    if (!questionText) {
      throw new StructuredQuestionTemplateError('Question text is required.')
    }
    rows.push({
      questionNumber: current.number.startsWith('Q') ? current.number : `Q${current.number}`,
      questionText,
      questionType: inferQuestionType(questionText, current.options),
      marks: current.marks,
      pageNumber: 1,
      parentQuestionNumber: null,
      options: current.options,
    })
    current = null
  }

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) continue

    const questionMatch = line.match(QUESTION_START)
    if (questionMatch) {
      flush()
      let remainder = (questionMatch[2] ?? '').trim()
      let prefixMarks: number | null = null
      const prefixMatch = remainder.match(QUESTION_PREFIX_MARKS)
      if (prefixMatch) {
        prefixMarks = Number(prefixMatch[1])
        remainder = prefixMatch[2].trim()
      } else {
        remainder = remainder.replace(/^[._):\-–—]+\s*/, '')
      }
      const extracted = extractVisibleMarks(remainder)
      current = {
        number: questionMatch[1].replace(/\s+/g, ''),
        parts: extracted.text ? [extracted.text] : [],
        options: [],
        marks: prefixMarks ?? extracted.marks,
      }
      continue
    }

    const optionMatch = line.match(OPTION_START)
    if (current && optionMatch) {
      current.options.push({ label: optionMatch[1].toUpperCase(), text: optionMatch[2].trim() })
      continue
    }

    if (!current) {
      current = {
        number: String(rows.length + 1),
        parts: [],
        options: [],
        marks: null,
      }
    }
    const extracted = extractVisibleMarks(line)
    current.parts.push(extracted.text)
    if (extracted.marks !== null) current.marks = extracted.marks
  }
  flush()

  if (rows.length === 0) {
    throw new StructuredQuestionTemplateError('Paste at least one question before importing.')
  }
  return rows
}

function csvEscape(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
}

export function structuredQuestionTemplateCsv(): string {
  const sample = [
    ['Q1', 'Which pattern constructs a complex object step by step?', '1', '', 'Singleton|Builder|Prototype|Adapter'],
    ['Q2', 'Explain why collisions are undesirable in cryptographic hash functions.', '2', 'short_answer', ''],
    ['Q3', 'A secure hash function should resist __________ attacks.', '', 'fill_in_blank', ''],
  ]
  return [STRUCTURED_QUESTION_TEMPLATE_HEADERS, ...sample]
    .map((record) => record.map(csvEscape).join(','))
    .join('\r\n')
}

export function downloadStructuredQuestionTemplate(): void {
  const blob = new Blob([structuredQuestionTemplateCsv()], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'Exam_Quality_Question_Template.csv'
  anchor.click()
  URL.revokeObjectURL(url)
}

export function applyStructuredQuestionRows(
  snapshot: ExtractionReviewSnapshot,
  rows: StructuredQuestionRow[],
  createId: () => string = () => crypto.randomUUID(),
): ExtractionReviewSnapshot {
  const questionIds = new Map(rows.map((row) => [row.questionNumber, createId()]))
  const questions: ExtractionReviewQuestion[] = rows.map((row, index) => ({
    source_record_id: questionIds.get(row.questionNumber) as string,
    included: true,
    parent_source_record_id: row.parentQuestionNumber
      ? questionIds.get(row.parentQuestionNumber) ?? null
      : null,
    number_label: row.questionNumber,
    question_text: row.questionText,
    page_number: row.pageNumber,
    marks: row.marks,
    sequence: index + 1,
    extraction_confidence: 1,
    geometry: null,
    question_type: row.questionType,
    instructions: null,
    extraction_method: 'structured_template',
    review_status: 'reviewed',
  }))
  const evidence: ExtractionReviewEvidence[] = questions.map((question) => ({
    source_record_id: createId(),
    included: true,
    question_source_record_id: question.source_record_id,
    source_document: 'exam',
    evidence_type: 'question_text',
    page_number: question.page_number,
    item_reference: question.number_label,
    extracted_text: question.question_text,
    extraction_confidence: 1,
    geometry: null,
  }))
  const questionOptions: ExtractionReviewQuestionOption[] = rows.flatMap((row) => {
    const questionId = questionIds.get(row.questionNumber) as string
    return row.options.map((option, index) => ({
      source_record_id: createId(),
      included: true,
      question_source_record_id: questionId,
      option_label: option.label,
      option_text: option.text,
      sequence: index + 1,
      page_number: row.pageNumber,
      extraction_confidence: 1,
      geometry: null,
    }))
  })
  const preservedEvidence = snapshot.evidence.filter(
    (item) => item.question_source_record_id === null,
  )
  return {
    ...snapshot,
    preparation_mode: 'structured_template',
    questions,
    question_options: questionOptions,
    question_blanks: [],
    question_source_spans: [],
    evidence: [...preservedEvidence, ...evidence],
    document_references: (snapshot.document_references ?? []).filter(
      (item) => item.question_source_record_id === null,
    ),
    reference_associations: [],
  }
}
