import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import {
  confirmExtractionReview,
  getExtractionReview,
  saveExtractionReview,
} from '../../api/analyses'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { PageState } from '../../components/ui/PageState'
import { Tabs, type TabItem } from '../../components/ui/Tabs'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError, localizeServerMessage } from '../../i18n/localizeError'
import type {
  ExtractionReviewClo,
  ExtractionReviewConfirmResponse,
  ExtractionReviewDocumentReference,
  ExtractionReviewEvidence,
  ExtractionReviewExtractionWarning,
  ExtractionReviewQuestion,
  ExtractionReviewQuestionBlank,
  ExtractionReviewQuestionOption,
  ExtractionReviewQuestionSourceSpan,
  ExtractionReviewResponse,
  ExtractionReviewSnapshot,
  ExtractionReviewSupportingAnnotation,
  ExtractionReviewSupportingMaterial,
  ExtractionReviewTopic,
  UploadedFileType,
  QuestionPreparationMode,
  QuestionType,
} from '../../types/api'
import { MethodologyLink } from '../analysis-results/MethodologyLink'
import { splitMaterialAnnotationText } from '../analysis-results/materialRelationships'
import { ExamPdfPreview } from './ExamPdfPreview'
import { unionGeometry, visualGeometryForQuestion } from './questionVisualGeometry'
import {
  applyPastedQuestionRows,
  applyStructuredQuestionRows,
  downloadStructuredQuestionTemplate,
  parsePastedQuestions,
  parseStructuredQuestionTemplate,
  StructuredQuestionTemplateError,
} from './structuredQuestionTemplate'
import { displayQuestionText } from '../../utils/questionText'

type ReviewTab = 'questions' | 'clos' | 'topics' | 'structured'
type EditableCollection =
  | 'questions'
  | 'question_options'
  | 'question_blanks'
  | 'clos'
  | 'topics'
  | 'supporting_materials'
  | 'supporting_annotations'
  | 'document_references'
type ReviewRecord =
  | ExtractionReviewQuestion
  | ExtractionReviewQuestionOption
  | ExtractionReviewQuestionBlank
  | ExtractionReviewClo
  | ExtractionReviewTopic
  | ExtractionReviewSupportingMaterial
  | ExtractionReviewSupportingAnnotation
  | ExtractionReviewDocumentReference

interface ExtractionReviewWorkspaceProps {
  analysisId: string
  onConfirmed: (response: ExtractionReviewConfirmResponse) => void
}

const SUPPORTED_QUESTION_TYPES: QuestionType[] = [
  'multiple_choice',
  'true_false',
  'fill_in_blank',
  'short_answer',
  'essay',
  'unknown',
]

const UNASSIGNED_ANSWER_SPACE = /^(?:[._·•…⋯\-–—=]\s*){4,}$/u
const UNASSIGNED_TABLE_HEADER = /^(?:no\.?\s*)?(?:statement|item)\s+(?:t\s*\/\s*f|true\s*\/\s*false)$/i
const UNASSIGNED_PAGE_FOOTER = /(?:synthetic test fixture|not an official document|نموذج تجريبي|مستند اصطناعي|غير تابع لأي جامعة)/i
const UNASSIGNED_PAGE_FRACTION = /^\d+\s*\/\s*\d+$/
const UNASSIGNED_SECTION_LABEL = /^(?:section|part|instructions?|choose\s+one|answer\s+all|true\s*\/\s*false|صح|خطأ)\b/i

export function isReviewableUnassignedCandidate(
  candidate: ExtractionReviewEvidence,
): boolean {
  if (candidate.question_source_record_id !== null) return false

  const text = candidate.extracted_text.replace(/\s+/g, ' ').trim()
  if (!text) return false
  if (UNASSIGNED_ANSWER_SPACE.test(text)) return false
  if (UNASSIGNED_TABLE_HEADER.test(text)) return false
  if (UNASSIGNED_PAGE_FOOTER.test(text)) return false
  if (UNASSIGNED_PAGE_FRACTION.test(text)) return false
  if (UNASSIGNED_SECTION_LABEL.test(text)) return false

  // Geometry-only PDF artifacts can survive as punctuation fragments. Keep
  // the audit row in the immutable snapshot, but do not ask the reviewer to
  // inspect it unless it contains at least one letter or digit.
  return /[\p{L}\p{N}]/u.test(text)
}

function questionTypeChoices(current: QuestionType | null | undefined): QuestionType[] {
  if (!current || SUPPORTED_QUESTION_TYPES.includes(current)) {
    return SUPPORTED_QUESTION_TYPES
  }
  return [current, ...SUPPORTED_QUESTION_TYPES]
}

function cloneSnapshot(snapshot: ExtractionReviewSnapshot): ExtractionReviewSnapshot {
  return JSON.parse(JSON.stringify(snapshot)) as ExtractionReviewSnapshot
}

function reviewRecordId(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID()
  }
  const bytes = new Uint8Array(16)
  globalThis.crypto?.getRandomValues?.(bytes)
  if (!bytes.some(Boolean)) {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256)
    }
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const value = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${value.slice(0, 8)}-${value.slice(8, 12)}-${value.slice(12, 16)}-${value.slice(16, 20)}-${value.slice(20)}`
}

function isManualQuestion(question: ExtractionReviewQuestion): boolean {
  return question.extraction_method === 'manual_review'
}

function isStructuredTemplateQuestion(question: ExtractionReviewQuestion): boolean {
  return question.extraction_method === 'structured_template'
}

function isPastedReviewQuestion(question: ExtractionReviewQuestion): boolean {
  return question.extraction_method === 'pasted_review'
}

function isReviewerAddedQuestion(question: ExtractionReviewQuestion): boolean {
  return isManualQuestion(question) || isStructuredTemplateQuestion(question) || isPastedReviewQuestion(question)
}

function addedQuestionIssues(snapshot: ExtractionReviewSnapshot): string[] {
  const issues: string[] = []
  for (const question of snapshot.questions) {
    if (
      !question.included ||
      !isReviewerAddedQuestion(question)
    ) {
      continue
    }
    if (
      !question.number_label.trim() ||
      !question.question_text.trim() ||
      (isManualQuestion(question) && !question.geometry)
    ) {
      issues.push(question.source_record_id)
      continue
    }
    const evidence = snapshot.evidence.filter(
      (item) =>
        item.question_source_record_id === question.source_record_id &&
        item.evidence_type === 'question_text',
    )
    if (
      evidence.length !== 1 ||
      !evidence[0].included ||
      evidence[0].page_number !== question.page_number ||
      JSON.stringify(evidence[0].geometry) !== JSON.stringify(question.geometry)
    ) {
      issues.push(question.source_record_id)
    }
  }
  return issues
}

function addedCourseSpecificationIssues(
  snapshot: ExtractionReviewSnapshot,
  original: ExtractionReviewSnapshot,
): string[] {
  const issues: string[] = []
  const originalCloIds = new Set(original.clos.map((item) => item.source_record_id))
  const originalTopicIds = new Set(original.topics.map((item) => item.source_record_id))
  for (const clo of snapshot.clos) {
    if (originalCloIds.has(clo.source_record_id) || !clo.included) continue
    if (!clo.code.trim() || !clo.text.trim() || !clo.geometry) {
      issues.push(clo.source_record_id)
    }
  }
  for (const topic of snapshot.topics) {
    if (originalTopicIds.has(topic.source_record_id) || !topic.included) continue
    if (!topic.text.trim() || !topic.geometry) {
      issues.push(topic.source_record_id)
    }
  }
  return issues
}

function withManualCourseSpecificationEvidence(
  snapshot: ExtractionReviewSnapshot,
  original: ExtractionReviewSnapshot,
): ExtractionReviewSnapshot {
  const next = cloneSnapshot(snapshot)
  const originalCloIds = new Set(original.clos.map((item) => item.source_record_id))
  const originalTopicIds = new Set(original.topics.map((item) => item.source_record_id))
  const originalEvidenceIds = new Set(original.evidence.map((item) => item.source_record_id))
  next.evidence = next.evidence.filter(
    (item) =>
      originalEvidenceIds.has(item.source_record_id) ||
      item.source_document !== 'tp153' ||
      (item.evidence_type !== 'clo' && item.evidence_type !== 'topic'),
  )

  function upsertEvidence(
    kind: 'clo' | 'topic',
    pageNumber: number,
    geometry: ExtractionReviewClo['geometry'],
    reference: string,
    text: string,
    included: boolean,
  ): void {
    if (!geometry) return
    const existing = next.evidence.find(
      (item) =>
        item.source_document === 'tp153' &&
        item.evidence_type === kind &&
        item.question_source_record_id === null &&
        item.page_number === pageNumber &&
        JSON.stringify(item.geometry) === JSON.stringify(geometry),
    )
    if (existing) {
      existing.included = included
      existing.item_reference = reference
      existing.extracted_text = text
      return
    }
    next.evidence.push({
      source_record_id: reviewRecordId(),
      included,
      question_source_record_id: null,
      source_document: 'tp153',
      evidence_type: kind,
      page_number: pageNumber,
      item_reference: reference,
      extracted_text: text,
      extraction_confidence: 1,
      geometry,
    })
  }

  for (const clo of next.clos) {
    if (originalCloIds.has(clo.source_record_id)) continue
    upsertEvidence('clo', clo.page_number, clo.geometry, clo.code, clo.text, clo.included)
  }
  for (const topic of next.topics) {
    if (originalTopicIds.has(topic.source_record_id)) continue
    upsertEvidence(
      'topic',
      topic.page_number,
      topic.geometry,
      topic.code || topic.text.slice(0, 100),
      topic.text,
      topic.included,
    )
  }
  return next
}

function replaceRecord<T extends ReviewRecord>(
  items: T[],
  sourceRecordId: string,
  patch: Partial<T>,
): T[] {
  return items.map((item) =>
    item.source_record_id === sourceRecordId ? { ...item, ...patch } : item,
  )
}

function questionDescendants(
  questions: ExtractionReviewQuestion[],
  sourceRecordId: string,
): Set<string> {
  const excludedIds = new Set([sourceRecordId])
  let changed = true
  while (changed) {
    changed = false
    for (const question of questions) {
      if (
        question.parent_source_record_id &&
        excludedIds.has(question.parent_source_record_id) &&
        !excludedIds.has(question.source_record_id)
      ) {
        excludedIds.add(question.source_record_id)
        changed = true
      }
    }
  }
  return excludedIds
}

function questionAncestors(
  questions: ExtractionReviewQuestion[],
  sourceRecordId: string,
): Set<string> {
  const questionsById = new Map(questions.map((question) => [question.source_record_id, question]))
  const includedIds = new Set([sourceRecordId])
  let parentId = questionsById.get(sourceRecordId)?.parent_source_record_id ?? null
  while (parentId) {
    includedIds.add(parentId)
    parentId = questionsById.get(parentId)?.parent_source_record_id ?? null
  }
  return includedIds
}

function updateSnapshotRecord(
  snapshot: ExtractionReviewSnapshot,
  collection: EditableCollection,
  sourceRecordId: string,
  patch: Partial<ReviewRecord>,
): ExtractionReviewSnapshot {
  if (collection === 'questions' && patch.included === false) {
    const excludedIds = questionDescendants(snapshot.questions, sourceRecordId)
    return {
      ...snapshot,
      questions: snapshot.questions.map((question) =>
        excludedIds.has(question.source_record_id)
          ? {
              ...question,
              ...(question.source_record_id === sourceRecordId ? patch : {}),
              included: false,
            }
          : question,
      ),
      evidence: snapshot.evidence.map((evidence) =>
        evidence.question_source_record_id &&
        excludedIds.has(evidence.question_source_record_id)
          ? { ...evidence, included: false }
          : evidence,
      ),
      question_options: (snapshot.question_options ?? []).map((option) =>
        excludedIds.has(option.question_source_record_id)
          ? { ...option, included: false }
          : option,
      ),
      question_blanks: (snapshot.question_blanks ?? []).map((blank) =>
        excludedIds.has(blank.question_source_record_id)
          ? { ...blank, included: false }
          : blank,
      ),
    }
  }

  if (collection === 'questions' && patch.included === true) {
    const includedIds = questionAncestors(snapshot.questions, sourceRecordId)
    return {
      ...snapshot,
      questions: snapshot.questions.map((question) =>
        includedIds.has(question.source_record_id)
          ? {
              ...question,
              ...(question.source_record_id === sourceRecordId ? patch : {}),
              included: true,
            }
          : question,
      ),
    }
  }


  const items = (snapshot[collection] ?? []) as ReviewRecord[]
  return {
    ...snapshot,
    [collection]: replaceRecord(items, sourceRecordId, patch),
  } as ExtractionReviewSnapshot
}

function confidencePercent(value: number): string {
  return `${Math.round(value * 100)}%`
}


function optionalNumber(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

function extractionCandidateProvenance(evidenceType: string): {
  pipeline: string
  provenance: string
} {
  const value = evidenceType.replace('extraction_candidate_', '')
  if (value.startsWith('local_')) {
    return { pipeline: 'local', provenance: value.slice('local_'.length) }
  }
  if (value.startsWith('gemini_')) {
    return { pipeline: 'Gemini', provenance: value.slice('gemini_'.length) }
  }
  return { pipeline: 'unknown', provenance: value }
}

interface ExtractionWarningGroup {
  key: string
  code: string
  severity: ExtractionReviewExtractionWarning['severity']
  pageNumber: number | null
  items: ExtractionReviewExtractionWarning[]
}

interface QuestionReviewCue {
  key: string
  code: string
  message: string
  pageNumber: number | null
  blocking: boolean
}

function friendlyQuestionReviewCue(code: string): string {
  const normalized = code.trim().toUpperCase()
  const messages: Record<string, string> = {
    MARKS_MISMATCH: 'Check the section and child marks against the PDF.',
    QUESTION_HIERARCHY_MISMATCH: 'Check that this question is attached to the correct section.',
    QUESTION_NUMBER_MISMATCH: 'Check this question number against the PDF.',
    SHARED_INSTRUCTIONS_MISMATCH: 'Check the shared instructions for this question.',
    TECHNICAL_TEXT_MISMATCH: 'Check the technical text and symbols against the PDF.',
    FIGURE_ASSOCIATION_UNCERTAIN: 'Check that the correct figure belongs with this question.',
    LOW_EXTRACTION_CONFIDENCE: 'Check this question against the PDF because extraction confidence is lower.',
    UNSUPPORTED_PILOT_QUESTION_TYPE: 'Confirm the question type manually against the PDF.',
  }
  return messages[normalized] ?? 'Check this question against the original PDF.'
}

function geometriesOverlap(
  left: ExtractionReviewQuestion['geometry'],
  right: ExtractionReviewQuestion['geometry'],
): boolean {
  if (!left || !right) return false
  return left.x0 <= right.x1 && left.x1 >= right.x0 && left.top <= right.bottom && left.bottom >= right.top
}

function groupExtractionWarnings(
  warnings: ExtractionReviewExtractionWarning[],
): ExtractionWarningGroup[] {
  const groups = new Map<string, ExtractionWarningGroup>()
  for (const warning of warnings) {
    const key = `${warning.severity}:${warning.code}:${warning.page_number ?? 'document'}`
    const existing = groups.get(key)
    if (existing) {
      existing.items.push(warning)
    } else {
      groups.set(key, {
        key,
        code: warning.code,
        severity: warning.severity,
        pageNumber: warning.page_number,
        items: [warning],
      })
    }
  }
  const severityOrder = { critical: 0, warning: 1, info: 2 }
  return [...groups.values()].sort(
    (left, right) =>
      severityOrder[left.severity] - severityOrder[right.severity] ||
      (left.pageNumber ?? -1) - (right.pageNumber ?? -1) ||
      left.code.localeCompare(right.code),
  )
}

function RecordHeader({
  title,
  included,
  pageNumber,
  confidence,
  disabled,
  includeControlDisabled = false,
  hierarchyLabel,
  onIncludedChange,
  onRestore,
}: {
  title: string
  included: boolean
  pageNumber: number
  confidence: number
  disabled: boolean
  includeControlDisabled?: boolean
  hierarchyLabel?: string
  onIncludedChange: (included: boolean) => void
  onRestore: () => void
}) {
  const { t } = useI18n()
  return (
    <div className="review-record-header">
      <div>
        <div className="review-record-title-line">
          <h3><bdi>{title}</bdi></h3>
          {hierarchyLabel && <span className="review-hierarchy-badge">{hierarchyLabel}</span>}
        </div>
        <p className="review-source-anchor">
          {t('Page')} {pageNumber} · {confidencePercent(confidence)} {t('extraction confidence')}
        </p>
      </div>
      <div className="review-record-controls">
        <label className="review-include-control">
          <input
            type="checkbox"
            checked={included}
            disabled={disabled || includeControlDisabled}
            onChange={(event) => onIncludedChange(event.target.checked)}
          />
          {t('Include in analysis')}
        </label>
        <Button variant="ghost" disabled={disabled} onClick={onRestore}>
          {t('Restore machine value')}
        </Button>
      </div>
    </div>
  )
}


function EmptyCollection({ label }: { label: string }) {
  const { t } = useI18n()
  return (
    <PageState
      state="empty"
      title={`${t('No')} ${t(label)}`}
      message={t('The empty collection is preserved as source evidence; do not create replacement official records here.')}
    />
  )
}



function QuestionsPanel({
  items,
  original,
  options,
  originalOptions,
  blanks,
  originalBlanks,
  sourceSpans,
  candidateEvidence,
  supportingMaterials,
  preparationMode,
  disabled,
  onChange,
  onOptionChange,
  onBlankChange,
  onSelect,
  selectedPage,
  onAddQuestion,
  onSplitQuestion,
  onMergeQuestion,
  onRemoveManualQuestion,
  reviewCuesByQuestion,
  requestedQuestionId,
}: {
  items: ExtractionReviewQuestion[]
  original: ExtractionReviewQuestion[]
  options: ExtractionReviewQuestionOption[]
  originalOptions: ExtractionReviewQuestionOption[]
  blanks: ExtractionReviewQuestionBlank[]
  originalBlanks: ExtractionReviewQuestionBlank[]
  sourceSpans: ExtractionReviewQuestionSourceSpan[]
  candidateEvidence: ExtractionReviewEvidence[]
  supportingMaterials: ExtractionReviewSupportingMaterial[]
  preparationMode: QuestionPreparationMode
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewQuestion>) => void
  onOptionChange: (id: string, patch: Partial<ExtractionReviewQuestionOption>) => void
  onBlankChange: (id: string, patch: Partial<ExtractionReviewQuestionBlank>) => void
  onSelect: (
    pageNumber: number,
    geometry: ExtractionReviewQuestion['geometry'],
    questionSourceRecordId?: string,
  ) => void
  selectedPage: number
  onAddQuestion: (pageNumber: number) => string
  onSplitQuestion: (sourceRecordId: string) => string
  onMergeQuestion: (sourceRecordId: string) => string | null
  onRemoveManualQuestion: (sourceRecordId: string) => void
  reviewCuesByQuestion: Map<string, QuestionReviewCue[]>
  requestedQuestionId: string | null
}) {
  const { t } = useI18n()
  const [expandedQuestionId, setExpandedQuestionId] = useState<string | null>(
    items[0]?.source_record_id ?? null,
  )
  const requestedQuestionExists = requestedQuestionId !== null
    && items.some((item) => item.source_record_id === requestedQuestionId)
  const expandedQuestionExists = expandedQuestionId !== null
    && items.some((item) => item.source_record_id === expandedQuestionId)
  const effectiveExpandedQuestionId = requestedQuestionExists
    ? requestedQuestionId
    : expandedQuestionExists
      ? expandedQuestionId
      : items[0]?.source_record_id ?? null
  useEffect(() => {
    if (!requestedQuestionExists || !requestedQuestionId) return undefined
    const timer = globalThis.setTimeout(() => {
      setExpandedQuestionId(requestedQuestionId)
    }, 0)
    return () => globalThis.clearTimeout(timer)
  }, [requestedQuestionExists, requestedQuestionId])
  if (!items.length) {
    const structured = preparationMode === 'structured_template'
    const manual = preparationMode === 'manual_pdf'
    return (
      <div className="review-question-empty">
        <PageState
          state="empty"
          title={t(
            structured
              ? 'No pasted or imported questions are available'
              : manual
                ? 'No manual questions have been added'
                : 'No questions were detected automatically',
          )}
          message={t(
            structured
              ? 'Paste questions or import the simple CSV above, then review them against the original PDF.'
              : 'Use the original PDF to add each visible question region before analysis.',
          )}
        />
        {!structured && (
          <Button
            disabled={disabled}
            onClick={() => {
              const id = onAddQuestion(selectedPage)
              setExpandedQuestionId(id)
            }}
          >
            {t('Add missing question from PDF')}
          </Button>
        )}
      </div>
    )
  }
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  const originalOptionsById = new Map(
    originalOptions.map((item) => [item.source_record_id, item]),
  )
  const originalBlanksById = new Map(
    originalBlanks.map((item) => [item.source_record_id, item]),
  )
  const childrenByParent = new Map<string, ExtractionReviewQuestion[]>()
  for (const item of items) {
    if (!item.parent_source_record_id) continue
    const children = childrenByParent.get(item.parent_source_record_id) ?? []
    children.push(item)
    childrenByParent.set(item.parent_source_record_id, children)
  }
  const itemsById = new Map(items.map((item) => [item.source_record_id, item]))
  function depth(item: ExtractionReviewQuestion): number {
    let current = item.parent_source_record_id
    let result = 0
    while (current && itemsById.has(current)) {
      result += 1
      current = itemsById.get(current)?.parent_source_record_id ?? null
    }
    return result
  }

  const unassignedCandidates = candidateEvidence.filter(isReviewableUnassignedCandidate)
  const structuredMode = preparationMode === 'structured_template'

  return (
    <div className="review-record-list review-question-list">
      <div className="review-question-toolbar">
        <div>
          <strong>{t(structuredMode ? 'Structured question review' : 'Human-assisted visual review')}</strong>
          <p>{t(
            structuredMode
              ? 'Compare every imported row with the original PDF. Marks may remain empty when they are not visibly written.'
              : 'Add or correct question regions using the original PDF before saving.',
          )}</p>
        </div>
        {!structuredMode && (
          <Button
            disabled={disabled}
            onClick={() => {
              const id = onAddQuestion(selectedPage)
              setExpandedQuestionId(id)
            }}
          >
            {t('Add missing question from PDF')}
          </Button>
        )}
      </div>
      {unassignedCandidates.length > 0 && (
        <details className="review-technical-diagnostics review-unassigned-details">
          <summary>{t('Unassigned visible candidates')}</summary>
          <p>{t('These source lines are retained for audit. Review them only when they contain missing question content.')}</p>
          {unassignedCandidates.map((candidate) => {
              return (
                <div className="review-candidate" key={candidate.source_record_id}>
                  <strong>{t('Possible missing question content')}</strong>
                  <p><bdi>{candidate.extracted_text}</bdi></p>
                  <Button
                    variant="ghost"
                    onClick={() => onSelect(candidate.page_number, candidate.geometry)}
                  >
                    {t('Show in PDF')}
                  </Button>
                </div>
              )
            })}
        </details>
      )}
      {items.map((item, itemIndex) => {
        const children = childrenByParent.get(item.source_record_id) ?? []
        const isContainer = children.length > 0
        const hasCompleteChildMarks = children.length > 0 && children.every((child) => child.marks !== null)
        const childMarks = hasCompleteChildMarks
          ? children.reduce((total, child) => total + (child.marks ?? 0), 0)
          : null
        const parent = item.parent_source_record_id
          ? itemsById.get(item.parent_source_record_id)
          : undefined
        const reviewCues = reviewCuesByQuestion.get(item.source_record_id) ?? []
        const itemOptions = options.filter(
          (option) => option.question_source_record_id === item.source_record_id,
        )
        const itemBlanks = blanks.filter(
          (blank) => blank.question_source_record_id === item.source_record_id,
        )
        const visualGeometry = visualGeometryForQuestion(
          item,
          items,
          options,
          blanks,
          sourceSpans,
          supportingMaterials,
        )
        const isExpanded = effectiveExpandedQuestionId === item.source_record_id
        const sourceProviders = [
          ...new Set(
            sourceSpans
              .filter(
                (span) =>
                  span.question_source_record_id === item.source_record_id &&
                  span.option_source_record_id === null,
              )
              .map((span) => span.provider),
          ),
        ]
        const showOptions = item.question_type === 'multiple_choice'
        const showBlanks = item.question_type === 'fill_in_blank'
        const requiresManualTypeReview = !SUPPORTED_QUESTION_TYPES.includes(
          item.question_type ?? 'unknown',
        )
        const previousMergeCandidate = items
          .slice(0, itemIndex)
          .reverse()
          .find((candidate) => candidate.included && candidate.page_number === item.page_number)
        const canMerge = Boolean(previousMergeCandidate) && !isContainer
        return (
          <Card
            as="article"
            id={`review-question-${item.source_record_id}`}
            className={`${!item.included ? 'review-record review-record--excluded' : 'review-record'}${isContainer ? ' review-record--container' : ''}${isExpanded ? ' review-record--expanded' : ''}`}
            key={item.source_record_id}
            style={{ '--question-depth': depth(item) } as CSSProperties}
          >
            <RecordHeader
              title={item.number_label ? `${t('Question')} ${item.number_label}` : t('New question')}
              included={item.included}
              pageNumber={item.page_number}
              confidence={item.extraction_confidence}
              disabled={disabled}
              includeControlDisabled={isContainer}
              hierarchyLabel={isContainer ? t('Parent / Container Question') : item.parent_source_record_id ? t('Child question') : undefined}
              onIncludedChange={(included) => onChange(item.source_record_id, { included })}
              onRestore={() => {
                const value = originals.get(item.source_record_id)
                if (value) onChange(item.source_record_id, value)
              }}
            />
            <div className="review-question-summary">
              <p dir="auto" className="review-question-summary__text bidi-plaintext">
                {displayQuestionText(item.question_text, item.number_label)}
              </p>
              <div className="review-question-summary__meta">
                <span>{isContainer ? t('Structural container') : t(item.question_type ?? 'unknown')}</span>
                <span>
                  {item.marks === null
                    ? parent?.marks !== null && parent?.marks !== undefined
                      ? `${t('No individual mark specified; section total')}: ${parent.marks}`
                      : t('Marks not detected')
                    : `${item.marks} ${t('Marks')}`}
                </span>
                {showOptions && itemOptions.length > 0 && <span>{itemOptions.length} {t('Answer options')}</span>}
                {showBlanks && itemBlanks.length > 0 && <span>{itemBlanks.length} {t('Detected blanks')}</span>}
                {false && requiresManualTypeReview && (
                  <span className="review-question-summary__manual">
                    {t('Manual visual review required')}
                  </span>
                )}
                {false && reviewCues.length > 0 && (
                  <span className="review-question-summary__needs-review">
                    {t('Needs review')}
                  </span>
                )}
              </div>
              {false && reviewCues.length > 0 && (
                <details className="review-question-cues">
                  <summary>{t('Why this question needs review')}</summary>
                  <ul>
                    {[...new Set(reviewCues.map((cue) => friendlyQuestionReviewCue(cue.code)))].map((message) => (
                      <li key={message}>{t(message)}</li>
                    ))}
                  </ul>
                </details>
              )}
              <div className="review-question-summary__actions">
                <Button
                  variant="secondary"
                  onClick={() => setExpandedQuestionId(isExpanded ? null : item.source_record_id)}
                >
                  {isExpanded ? t('Hide review details') : t('Review question')}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => onSelect(item.page_number, visualGeometry, item.source_record_id)}
                >
                  {t('Show in PDF')}
                </Button>
                {!structuredMode && (
                  <Button
                    variant="ghost"
                    disabled={disabled || !item.included}
                    onClick={() => {
                      const id = onSplitQuestion(item.source_record_id)
                      setExpandedQuestionId(id)
                    }}
                  >
                    {t('Split / add second part')}
                  </Button>
                )}
                {!structuredMode && canMerge && (
                  <Button
                    variant="ghost"
                    disabled={disabled || !item.included}
                    onClick={() => {
                      const id = onMergeQuestion(item.source_record_id)
                      if (id) setExpandedQuestionId(id)
                    }}
                  >
                    {t('Merge with previous question')}
                  </Button>
                )}
                {(isManualQuestion(item) || isPastedReviewQuestion(item)) && (
                  <Button
                    variant="ghost"
                    disabled={disabled}
                    onClick={() => {
                      onRemoveManualQuestion(item.source_record_id)
                      setExpandedQuestionId(null)
                    }}
                  >
                    {t('Remove added question')}
                  </Button>
                )}
              </div>
            </div>
            {isExpanded && (
              <div className="review-question-expanded">
                {isManualQuestion(item) && (!item.geometry || !item.question_text.trim()) && (
                  <Alert variant="warning" title={t('Complete the added question')}>
                    {t('Select its complete region in the PDF, then enter the question text before saving.')}
                  </Alert>
                )}
                {isPastedReviewQuestion(item) && !item.question_text.trim() && (
                  <Alert variant="warning" title={t('Complete the pasted question')}>
                    {t('Enter the source-faithful question text before saving.')}
                  </Alert>
                )}
                <Alert variant="info" title={t('Use the PDF as the source reference')}>
                  {t('The original page is shown on the left. Use Show in PDF to verify the complete question and adjust the highlighted region only when needed.')}
                </Alert>

                {isContainer && (
                  <Alert variant="info" title={t('Parent / Container Question')}>
                    <p>{t('This structural question groups the sub-questions below and is not scored as an independent semantic item.')}</p>
                    {childMarks === null ? (
                      <p>{t('The section total is authoritative; individual child marks may remain blank.')}</p>
                    ) : (
                      <p>{t('Sub-question marks total')}: <strong>{childMarks}</strong></p>
                    )}
                  </Alert>
                )}

                <section className="review-editable-question" aria-label={t('Editable extracted data')}>
                  <div className="review-section-heading">
                    <h4>{t('Editable extracted data')}</h4>
                    <p>{t('Correct the proposal only when it differs from the original PDF shown on the left.')}</p>
                  </div>
                  <div className="review-form-grid review-form-grid--primary">
                    <label>
                      {t('Question number')}
                      <input
                        dir="auto"
                        value={item.number_label}
                        disabled={disabled || !item.included}
                        onChange={(event) =>
                          onChange(item.source_record_id, { number_label: event.target.value })
                        }
                      />
                    </label>
                    <label>
                      {t('Question type')}
                      <select
                        value={item.question_type ?? 'unknown'}
                        disabled={disabled || !item.included}
                        onChange={(event) =>
                          onChange(item.source_record_id, {
                            question_type: event.target.value as QuestionType,
                          })
                        }
                      >
                        {questionTypeChoices(item.question_type).map((questionType) => (
                          <option value={questionType} key={questionType}>
                            {t(questionType)}
                            {!SUPPORTED_QUESTION_TYPES.includes(questionType)
                              ? ` — ${t('Requires manual review')}`
                              : ''}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      {t('Marks')}
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={item.marks ?? ''}
                        placeholder={t('Not detected')}
                        disabled={disabled || !item.included}
                        onChange={(event) =>
                          onChange(item.source_record_id, { marks: optionalNumber(event.target.value) })
                        }
                      />
                    </label>
                    <label className="review-field-wide">
                      {t('Question text')}
                      <textarea
                        dir="auto"
                        rows={4}
                        value={displayQuestionText(item.question_text, item.number_label)}
                        disabled={disabled || !item.included}
                        onChange={(event) =>
                          onChange(item.source_record_id, { question_text: event.target.value })
                        }
                      />
                    </label>
                  </div>
                </section>

                {showOptions && (
                  <section className="review-question-options">
                    <h4>{t('Answer options')}</h4>
                    {itemOptions.length === 0 ? (
                      <p>{t('No answer options were detected for this question.')}</p>
                    ) : itemOptions.map((option) => (
                      <div
                        className={!option.included ? 'review-option review-record--excluded' : 'review-option'}
                        key={option.source_record_id}
                      >
                        <label>
                          <input
                            type="checkbox"
                            checked={option.included}
                            disabled={disabled || !item.included}
                            onChange={(event) =>
                              onOptionChange(option.source_record_id, { included: event.target.checked })
                            }
                          />
                          {t('Include option')}
                        </label>
                        <input
                          aria-label={t('Option label')}
                          dir="auto"
                          value={option.option_label}
                          disabled={disabled || !item.included || !option.included}
                          onChange={(event) =>
                            onOptionChange(option.source_record_id, { option_label: event.target.value })
                          }
                        />
                        <textarea
                          aria-label={t('Option text')}
                          dir="auto"
                          value={option.option_text}
                          disabled={disabled || !item.included || !option.included}
                          onChange={(event) =>
                            onOptionChange(option.source_record_id, { option_text: event.target.value })
                          }
                        />
                        <Button
                          variant="ghost"
                          disabled={disabled}
                          onClick={() => {
                            const machine = originalOptionsById.get(option.source_record_id)
                            if (machine) onOptionChange(option.source_record_id, machine)
                          }}
                        >
                          {t('Restore machine value')}
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => onSelect(
                            option.page_number,
                            option.geometry,
                            item.source_record_id,
                          )}
                        >
                          {t('Show in PDF')}
                        </Button>
                      </div>
                    ))}
                  </section>
                )}

                {showBlanks && (
                  <details className="review-optional-structure">
                    <summary>
                      {t('Detected blanks')} ({itemBlanks.length})
                    </summary>
                    <p>{t('Blank details are optional review aids and are not a replacement for the original question image.')}</p>
                    {itemBlanks.map((blank) => (
                      <div
                        className={!blank.included ? 'review-option review-record--excluded' : 'review-option'}
                        key={blank.source_record_id}
                      >
                        <label>
                          <input
                            type="checkbox"
                            checked={blank.included}
                            disabled={disabled || !item.included}
                            onChange={(event) =>
                              onBlankChange(blank.source_record_id, { included: event.target.checked })
                            }
                          />
                          {t('Include blank')} {blank.blank_index}
                        </label>
                        <input
                          aria-label={`${t('Blank source text')} ${blank.blank_index}`}
                          dir="auto"
                          value={blank.source_text ?? ''}
                          disabled={disabled || !item.included || !blank.included}
                          onChange={(event) =>
                            onBlankChange(blank.source_record_id, {
                              source_text: event.target.value || null,
                            })
                          }
                        />
                        <Button
                          variant="ghost"
                          disabled={disabled}
                          onClick={() => {
                            const machine = originalBlanksById.get(blank.source_record_id)
                            if (machine) onBlankChange(blank.source_record_id, machine)
                          }}
                        >
                          {t('Restore machine value')}
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => onSelect(
                            blank.page_number,
                            blank.geometry,
                            item.source_record_id,
                          )}
                        >
                          {t('Show in PDF')}
                        </Button>
                      </div>
                    ))}
                  </details>
                )}

                <details className="review-audit-details review-question-advanced">
                  <summary>{t('Advanced structure and extraction details')}</summary>
                  <div className="review-form-grid">
                    <label>
                      {t('Parent question')}
                      <select
                        aria-label={t('Parent question')}
                        value={item.parent_source_record_id ?? ''}
                        disabled={disabled || !item.included}
                        onChange={(event) =>
                          onChange(item.source_record_id, {
                            parent_source_record_id: event.target.value || null,
                          })
                        }
                      >
                        <option value="">{t('Top-level question')}</option>
                        {items
                          .filter((candidate) =>
                            candidate.included &&
                            !questionDescendants(items, item.source_record_id).has(candidate.source_record_id),
                          )
                          .map((candidate) => (
                            <option value={candidate.source_record_id} key={candidate.source_record_id}>
                              {candidate.number_label} — {candidate.question_text.slice(0, 60)}
                            </option>
                          ))}
                      </select>
                    </label>
                    <label className="review-field-wide">
                      {t('Instructions')}
                      <textarea
                        dir="auto"
                        rows={2}
                        value={item.instructions ?? ''}
                        disabled={disabled || !item.included}
                        onChange={(event) =>
                          onChange(item.source_record_id, {
                            instructions: event.target.value || null,
                          })
                        }
                      />
                    </label>
                  </div>
                  <p className="review-source-anchor">
                    {t('Extraction method')}: {t(item.extraction_method ?? 'legacy')}
                    {' · '}
                    {t('Source providers')}: {sourceProviders.join(', ') || t('Unavailable')}
                  </p>
                  <div className="review-candidate-comparison">
                    <h4>{t('Extraction candidates')}</h4>
                    <p><strong>{t('Canonical proposed value')}:</strong> <bdi>{item.question_text}</bdi></p>
                    {candidateEvidence
                      .filter((candidate) => candidate.question_source_record_id === item.source_record_id)
                      .map((candidate) => {
                        const source = extractionCandidateProvenance(candidate.evidence_type)
                        return (
                          <div className="review-candidate" key={candidate.source_record_id}>
                            <strong>{t('Source/provenance')}: {t(source.pipeline)} / {t(source.provenance)}</strong>
                            <p><bdi>{candidate.extracted_text}</bdi></p>
                          </div>
                        )
                      })}
                    {!candidateEvidence.some(
                      (candidate) => candidate.question_source_record_id === item.source_record_id,
                    ) && <p>{t('Local-only extraction')}</p>}
                  </div>
                </details>
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}


function ClosPanel({
  items,
  original,
  disabled,
  selectedPage,
  onChange,
  onAdd,
  onSelect,
}: {
  items: ExtractionReviewClo[]
  original: ExtractionReviewClo[]
  disabled: boolean
  selectedPage: number
  onChange: (id: string, patch: Partial<ExtractionReviewClo>) => void
  onAdd: (pageNumber: number) => string
  onSelect: (id: string, pageNumber: number, geometry: ExtractionReviewClo['geometry']) => void
}) {
  const { t } = useI18n()
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      <div className="review-panel-actions">
        <Button variant="secondary" disabled={disabled} onClick={() => onAdd(selectedPage)}>
          {t('Add missing CLO from Course Specification PDF')}
        </Button>
      </div>
      {!items.length && <EmptyCollection label="CLOs" />}
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={item.code || t('Added CLO')}
            included={item.included}
            pageNumber={item.page_number}
            confidence={item.extraction_confidence}
            disabled={disabled}
            onIncludedChange={(included) => onChange(item.source_record_id, { included })}
            onRestore={() => {
              const value = originals.get(item.source_record_id)
              if (value) onChange(item.source_record_id, value)
            }}
          />
          <div className="review-inline-actions">
            <Button
              variant="ghost"
              onClick={() => onSelect(item.source_record_id, item.page_number, item.geometry)}
            >
              {t('Show in Course Specification PDF')}
            </Button>
          </div>
          <div className="review-form-grid">
            <label>
              {t('CLO code')}
              <input
                dir="auto"
                value={item.code}
                disabled={disabled || !item.included}
                onChange={(event) => onChange(item.source_record_id, { code: event.target.value })}
              />
            </label>
            <label>
              {t('Program outcome reference')}
              <input
                value={item.program_outcome_reference ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, {
                    program_outcome_reference: event.target.value || null,
                  })
                }
              />
            </label>
            <label className="review-field-wide">
              {t('CLO text')}
              <textarea
                dir="auto"
                className="bidi-plaintext"
                rows={4}
                value={item.text}
                disabled={disabled || !item.included}
                onChange={(event) => onChange(item.source_record_id, { text: event.target.value })}
              />
            </label>
          </div>
        </Card>
      ))}
    </div>
  )
}

function TopicsPanel({
  items,
  original,
  disabled,
  selectedPage,
  onChange,
  onAdd,
  onSelect,
}: {
  items: ExtractionReviewTopic[]
  original: ExtractionReviewTopic[]
  disabled: boolean
  selectedPage: number
  onChange: (id: string, patch: Partial<ExtractionReviewTopic>) => void
  onAdd: (pageNumber: number) => string
  onSelect: (id: string, pageNumber: number, geometry: ExtractionReviewTopic['geometry']) => void
}) {
  const { t } = useI18n()
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      <div className="review-panel-actions">
        <Button variant="secondary" disabled={disabled} onClick={() => onAdd(selectedPage)}>
          {t('Add missing topic from Course Specification PDF')}
        </Button>
      </div>
      {!items.length && <EmptyCollection label="topics" />}
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={item.code ?? (item.text.slice(0, 50) || t('Added topic'))}
            included={item.included}
            pageNumber={item.page_number}
            confidence={item.extraction_confidence}
            disabled={disabled}
            onIncludedChange={(included) => onChange(item.source_record_id, { included })}
            onRestore={() => {
              const value = originals.get(item.source_record_id)
              if (value) onChange(item.source_record_id, value)
            }}
          />
          <div className="review-inline-actions">
            <Button
              variant="ghost"
              onClick={() => onSelect(item.source_record_id, item.page_number, item.geometry)}
            >
              {t('Show in Course Specification PDF')}
            </Button>
          </div>
          <div className="review-form-grid">
            <label>
              {t('Topic code')}
              <input
                value={item.code ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { code: event.target.value || null })
                }
              />
            </label>
            <label>
              {t('Expected hours')}
              <input
                type="number"
                min="0"
                step="any"
                value={item.expected_hours ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, {
                    expected_hours: optionalNumber(event.target.value),
                  })
                }
              />
            </label>
            <label className="review-field-wide">
              {t('Topic text')}
              <textarea
                dir="auto"
                className="bidi-plaintext"
                rows={4}
                value={item.text}
                disabled={disabled || !item.included}
                onChange={(event) => onChange(item.source_record_id, { text: event.target.value })}
              />
            </label>
          </div>
        </Card>
      ))}
    </div>
  )
}

function MaterialReviewCard({
  item,
  annotations,
  originalMaterial,
  originalAnnotations,
  questions,
  disabled,
  onChange,
}: {
  item: ExtractionReviewSupportingMaterial
  annotations: ExtractionReviewSupportingAnnotation[]
  originalMaterial: ExtractionReviewSupportingMaterial | undefined
  originalAnnotations: ExtractionReviewSupportingAnnotation[]
  questions: ExtractionReviewQuestion[]
  disabled: boolean
  onChange: (
    collection: EditableCollection,
    id: string,
    patch: Partial<ReviewRecord>,
  ) => void
}) {
  const { t } = useI18n()
  const labelAnnotation = annotations.find(
    (annotation) => annotation.annotation_type === 'label',
  )
  const captionAnnotation = annotations.find(
    (annotation) => annotation.annotation_type === 'caption',
  )
  const labelParts = labelAnnotation
    ? splitMaterialAnnotationText(labelAnnotation.original_text)
    : null
  const captionParts = captionAnnotation
    ? splitMaterialAnnotationText(captionAnnotation.original_text)
    : null

  function setIncluded(included: boolean): void {
    onChange('supporting_materials', item.source_record_id, { included })
    for (const annotation of annotations) {
      onChange('supporting_annotations', annotation.source_record_id, { included })
    }
  }

  function restoreMachineValue(): void {
    if (originalMaterial) {
      onChange('supporting_materials', item.source_record_id, originalMaterial)
    }
    for (const annotation of originalAnnotations) {
      onChange('supporting_annotations', annotation.source_record_id, annotation)
    }
  }

  return (
    <Card
      as="article"
      className="review-record-card review-material-card"
    >
      <RecordHeader
        title={t(item.material_type.replace('_', ' '))}
        included={item.included}
        pageNumber={item.page_number}
        confidence={item.extraction_confidence}
        disabled={disabled}
        onIncludedChange={setIncluded}
        onRestore={restoreMachineValue}
      />
      <div className="review-material-fields">
        <label>
          {t('Associated question')}
          <select
            value={item.question_source_record_id ?? ''}
            disabled={disabled || !item.included}
            onChange={(event) =>
              onChange('supporting_materials', item.source_record_id, {
                question_source_record_id: event.target.value || null,
              })
            }
          >
            <option value="">{t('Unassigned')}</option>
            {questions.filter((question) => question.included).map((question) => (
              <option value={question.source_record_id} key={question.source_record_id}>
                {question.number_label} — {question.question_text.slice(0, 60)}
              </option>
            ))}
          </select>
        </label>
        {labelAnnotation && (
          <label>
            {t('Reference label')}
            <input
              value={labelParts?.label ?? labelAnnotation.original_text}
              disabled={disabled || !item.included}
              dir="auto"
              className="bidi-plaintext"
              onChange={(event) =>
                onChange('supporting_annotations', labelAnnotation.source_record_id, {
                  original_text: event.target.value,
                })
              }
            />
          </label>
        )}
        {(captionAnnotation || labelParts?.remainder) && (
          <label className="review-field-wide">
            {t('Caption or title')}
            <textarea
              value={
                captionParts?.remainder ??
                captionAnnotation?.original_text ??
                labelParts?.remainder ??
                ''
              }
              disabled={disabled || !item.included || !captionAnnotation}
              dir="auto"
              className="bidi-plaintext"
              rows={2}
              onChange={(event) => {
                if (captionAnnotation) {
                  onChange(
                    'supporting_annotations',
                    captionAnnotation.source_record_id,
                    { original_text: event.target.value },
                  )
                }
              }}
            />
          </label>
        )}
        {item.source_text && (
          <label className="review-field-wide">
            {t('Extracted description')}
            <textarea
              value={item.source_text}
              disabled={disabled || !item.included}
              dir="auto"
              className="bidi-plaintext"
              rows={4}
              onChange={(event) =>
                onChange('supporting_materials', item.source_record_id, {
                  source_text: event.target.value,
                })
              }
            />
          </label>
        )}
      </div>
      <details className="review-audit-details">
        <summary>{t('Machine-extracted audit record')}</summary>
        {originalMaterial?.source_text && (
          <pre dir="auto" className="bidi-plaintext">
            {originalMaterial.source_text}
          </pre>
        )}
        {originalAnnotations.map((annotation) => (
          <p
            key={annotation.source_record_id}
            dir="auto"
            className="bidi-plaintext"
          >
            <strong>{t(annotation.annotation_type)}:</strong>{' '}
            <bdi dir="auto">{annotation.original_text}</bdi>
          </p>
        ))}
      </details>
    </Card>
  )
}

interface StructuredEvidencePanelProps {
  snapshot: ExtractionReviewSnapshot
  original: ExtractionReviewSnapshot
  disabled: boolean
  onChange: (
    collection: EditableCollection,
    id: string,
    patch: Partial<ReviewRecord>,
  ) => void
}

function StructuredEvidencePanel({
  snapshot,
  original,
  disabled,
  onChange,
}: StructuredEvidencePanelProps) {
  const { locale, t } = useI18n()
  const materials = snapshot.supporting_materials ?? []
  const annotations = snapshot.supporting_annotations ?? []
  const references = snapshot.document_references ?? []
  const associations = snapshot.reference_associations ?? []
  return (
    <div className="review-record-list">
      <h2>{t('Linked supporting context')} ({materials.length})</h2>
      <p className="review-section-note">
        {t(
          'Only high-confidence figures, tables, or code context explicitly needed by a question are shown. Confirm the linked question or exclude the item before continuing.',
        )}
      </p>
      {materials.length === 0 && (
        <p>{t('No question-linked supporting context was detected.')}</p>
      )}
      {materials.map((item) => {
        const materialAnnotations = annotations.filter(
          (annotation) =>
            annotation.material_source_record_id === item.source_record_id,
        )
        const originalMaterial = (original.supporting_materials ?? []).find(
          (candidate) => candidate.source_record_id === item.source_record_id,
        )
        const originalAnnotations = (original.supporting_annotations ?? []).filter(
          (annotation) =>
            annotation.material_source_record_id === item.source_record_id,
        )
        return (
          <MaterialReviewCard
            key={item.source_record_id}
            item={item}
            annotations={materialAnnotations}
            originalMaterial={originalMaterial}
            originalAnnotations={originalAnnotations}
            questions={snapshot.questions}
            disabled={disabled}
            onChange={onChange}
          />
        )
      })}

      {references.length > 0 && (
        <h2>{t('Explicit references')} ({references.length})</h2>
      )}
      {references.map((item) => (
        <Card as="article" key={item.source_record_id} className="review-record-card">
          <label>
            <input
              type="checkbox"
              checked={item.included}
              disabled={disabled}
              onChange={(event) =>
                onChange('document_references', item.source_record_id, {
                  included: event.target.checked,
                })
              }
            />
            {t('Include reference')}
          </label>
          <strong>{t('Original source text')}</strong>
          <p dir="auto">{item.original_text}</p>
          <label>
            {t('Associated question')}
            <select
              value={item.question_source_record_id ?? ''}
              disabled={disabled || !item.included}
              onChange={(event) =>
                onChange('document_references', item.source_record_id, {
                  question_source_record_id: event.target.value || null,
                })
              }
            >
              <option value="">{t('Unassigned')}</option>
              {snapshot.questions.filter((question) => question.included).map((question) => (
                <option value={question.source_record_id} key={question.source_record_id}>
                  {question.number_label} — {question.question_text.slice(0, 60)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Target label')}
            <input
              value={item.target_label}
              disabled={disabled || !item.included}
              dir="auto"
              onChange={(event) =>
                onChange('document_references', item.source_record_id, {
                  target_label: event.target.value,
                })
              }
            />
          </label>
          <p>{t('Resolution')}: {t(item.resolution_status)}</p>
        </Card>
      ))}

      {associations.length > 0 && (
        <details className="review-audit-details">
          <summary>
            {t('Association review details')} ({associations.length})
          </summary>
          <ul className="review-warning-list">
            {associations.map((item) => (
              <li key={item.source_record_id}>
                {item.selected
                  ? t('Uniquely linked material')
                  : item.basis === 'proximity_support'
                    ? t('Nearby material suggestion only')
                    : t('Possible matching material')}
                {item.ambiguity_reason
                  ? ` · ${
                      locale === 'ar'
                        ? t(
                            item.basis === 'proximity_support'
                              ? 'Proximity is supporting evidence only.'
                              : 'Multiple exact targets share this label.',
                          )
                        : item.ambiguity_reason
                    }`
                  : ''}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}


export function ExtractionReviewWorkspace({
  analysisId,
  onConfirmed,
}: ExtractionReviewWorkspaceProps) {
  const { locale, t } = useI18n()
  const [review, setReview] = useState<ExtractionReviewResponse | null>(null)
  const [draft, setDraft] = useState<ExtractionReviewSnapshot | null>(null)
  const [activeTab, setActiveTab] = useState<ReviewTab>('questions')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isConfirming, setIsConfirming] = useState(false)
  const [showWarningConfirmation, setShowWarningConfirmation] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [selectedPage, setSelectedPage] = useState(1)
  const [selectedGeometry, setSelectedGeometry] = useState<
    ExtractionReviewQuestion['geometry']
  >(null)
  const [pdfFocusRequest, setPdfFocusRequest] = useState(0)
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null)
  const [selectedCourseRecord, setSelectedCourseRecord] = useState<{
    collection: 'clos' | 'topics'
    id: string
  } | null>(null)
  const [requestedReviewQuestionId, setRequestedReviewQuestionId] = useState<string | null>(null)
  const [pastedQuestionsText, setPastedQuestionsText] = useState('')
  const [showStartOverTools, setShowStartOverTools] = useState(false)

  async function loadReview(): Promise<void> {
    setIsLoading(true)
    setError(null)
    try {
      const response = await getExtractionReview(analysisId)
      setReview(response)
      setDraft(cloneSnapshot(response.snapshot))
      if (response.snapshot.questions[0]) {
        setSelectedPage(response.snapshot.questions[0].page_number)
        setSelectedGeometry(response.snapshot.questions[0].geometry)
        setSelectedQuestionId(response.snapshot.questions[0].source_record_id)
      }
    } catch (loadError) {
      setError(localizeInterfaceError(loadError, locale, t, 'Could not load extraction review'))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    getExtractionReview(analysisId)
      .then((response) => {
        if (cancelled) return
        setReview(response)
        setDraft(cloneSnapshot(response.snapshot))
        if (response.snapshot.questions[0]) {
          setSelectedPage(response.snapshot.questions[0].page_number)
          setSelectedGeometry(response.snapshot.questions[0].geometry)
          setSelectedQuestionId(response.snapshot.questions[0].source_record_id)
        }
      })
      .catch((loadError: unknown) => {
        if (cancelled) return
        setError(localizeInterfaceError(loadError, locale, t, 'Could not load extraction review'))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [analysisId, locale, t])

  const isDirty = useMemo(
    () => Boolean(review && draft && JSON.stringify(review.snapshot) !== JSON.stringify(draft)),
    [draft, review],
  )
  const extractionWarningGroups = useMemo(
    () => groupExtractionWarnings(draft?.extraction_warnings ?? []),
    [draft?.extraction_warnings],
  )
  const groupedReviewWarnings = useMemo(() => {
    // The review workspace renders once before the API response arrives.
    // Keep the loading render safe instead of dereferencing null review data.
    if (!draft || !review) return []

    const grouped = new Map<
      string,
      { code: string; message: string; count: number; questionLabels: string[] }
    >()
    const questionById = new Map<string, string>(
      draft.questions.map((item) => [item.source_record_id, item.number_label]),
    )
    for (const warning of review.warnings) {
      const key = `${warning.code}::${warning.message}`
      const current = grouped.get(key) ?? {
        code: warning.code,
        message: warning.message,
        count: 0,
        questionLabels: [],
      }
      current.count += 1
      const label = warning.source_record_id
        ? questionById.get(warning.source_record_id)
        : undefined
      if (label && !current.questionLabels.includes(label)) current.questionLabels.push(label)
      grouped.set(key, current)
    }
    return [...grouped.values()]
  }, [draft, review])
  const technicalWarningCount = extractionWarningGroups.reduce(
    (count, group) => count + group.items.length,
    0,
  ) + groupedReviewWarnings.reduce((count, group) => count + group.count, 0)
  const questionReviewCuesByQuestion = useMemo(() => {
    const cues = new Map<string, QuestionReviewCue[]>()
    if (!draft || !review) return cues

    const blockingIds = new Set(review.blocking_extraction_warning_ids ?? [])
    const questionIdsBySourceLine = new Map<string, Set<string>>()
    for (const span of draft.question_source_spans ?? []) {
      const ids = questionIdsBySourceLine.get(span.source_line_id) ?? new Set<string>()
      ids.add(span.question_source_record_id)
      questionIdsBySourceLine.set(span.source_line_id, ids)
    }
    const addCue = (questionId: string, cue: QuestionReviewCue) => {
      const current = cues.get(questionId) ?? []
      if (!current.some((item) => item.key === cue.key)) current.push(cue)
      cues.set(questionId, current)
    }

    for (const warning of review.warnings) {
      if (warning.collection !== 'questions' || !warning.source_record_id) continue
      addCue(warning.source_record_id, {
        key: `review:${warning.code}:${warning.source_record_id}`,
        code: warning.code,
        message: warning.message,
        pageNumber: null,
        blocking: false,
      })
    }
    for (const warning of draft.extraction_warnings ?? []) {
      const affectedIds = new Set<string>()
      for (const sourceLineId of warning.source_line_ids) {
        for (const questionId of questionIdsBySourceLine.get(sourceLineId) ?? []) {
          affectedIds.add(questionId)
        }
      }
      if (affectedIds.size === 0 && warning.page_number && warning.geometry) {
        for (const question of draft.questions) {
          if (
            question.page_number === warning.page_number &&
            geometriesOverlap(question.geometry, warning.geometry)
          ) {
            affectedIds.add(question.source_record_id)
          }
        }
      }
      for (const questionId of affectedIds) {
        addCue(questionId, {
          key: `extraction:${warning.source_record_id}`,
          code: warning.code,
          message: warning.message,
          pageNumber: warning.page_number,
          blocking: blockingIds.has(warning.source_record_id),
        })
      }
    }
    return cues
  }, [draft, review])
  const flaggedQuestionIds = useMemo(
    () => [...questionReviewCuesByQuestion.keys()],
    [questionReviewCuesByQuestion],
  )
  const incompleteAddedQuestionIds = useMemo(
    () => (draft ? addedQuestionIssues(draft) : []),
    [draft],
  )
  const hasIncompleteAddedQuestions = incompleteAddedQuestionIds.length > 0
  const incompleteCourseSpecificationIds = useMemo(
    () => (draft && review
      ? addedCourseSpecificationIssues(draft, review.original_snapshot)
      : []),
    [draft, review],
  )
  const hasIncompleteCourseSpecificationRecords = incompleteCourseSpecificationIds.length > 0
  const hasIncompleteReviewRecords =
    hasIncompleteAddedQuestions || hasIncompleteCourseSpecificationRecords
  const includedQuestions = (draft?.questions ?? []).filter((item) => item.included)
  const includedQuestionCount = includedQuestions.length
  const structuralContainerIds = new Set(
    includedQuestions
      .filter((candidate) =>
        includedQuestions.some(
          (item) => item.parent_source_record_id === candidate.source_record_id,
        ),
      )
      .map((item) => item.source_record_id),
  )
  const structuralContainerCount = structuralContainerIds.size
  const assessedQuestionCount = includedQuestionCount - structuralContainerCount
  const preparationMode = draft?.preparation_mode ?? 'assisted_pdf'
  const extractionCandidateTypes = (draft?.evidence ?? [])
    .filter((item) => item.evidence_type.startsWith('extraction_candidate_'))
    .map((item) => item.evidence_type)
  const extractionVerificationLabel = extractionCandidateTypes.some((item) =>
    item.includes('_gemini_fresh_gemini'),
  )
    ? t('Gemini fresh')
    : extractionCandidateTypes.some((item) => item.includes('_gemini_cache'))
      ? t('Gemini cached')
      : t('Local only')

  function reviewFlaggedQuestions(): void {
    const questionId = flaggedQuestionIds[0]
    const question = draft?.questions.find((item) => item.source_record_id === questionId)
    if (!question) return
    setActiveTab('questions')
    setRequestedReviewQuestionId(questionId)
    selectPdfLocation(question.page_number, question.geometry, questionId)
    globalThis.setTimeout(() => {
      document.getElementById(`review-question-${questionId}`)?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      })
      setRequestedReviewQuestionId(null)
    }, 0)
  }

  function replaceVisibleDraftWithRows(
    rows: ReturnType<typeof parsePastedQuestions>,
  ): void {
    setDraft((current) => {
      if (!current) return current
      return current.preparation_mode === 'structured_template'
        ? applyStructuredQuestionRows(current, rows, reviewRecordId)
        : applyPastedQuestionRows(current, rows, reviewRecordId)
    })
    const first = rows[0]
    if (first) {
      setSelectedPage(first.pageNumber)
      setSelectedGeometry(null)
      setSelectedQuestionId(null)
    }
    setShowStartOverTools(false)
  }

  async function importStructuredTemplate(file: File): Promise<void> {
    setError(null)
    setNotice(null)
    try {
      const rows = parseStructuredQuestionTemplate(await file.text())
      replaceVisibleDraftWithRows(rows)
      setNotice(t(
        preparationMode === 'structured_template'
          ? 'Structured question template imported. Review every question before saving.'
          : 'The automatic draft was replaced with the imported question list. Review it before saving.',
      ))
    } catch (importError) {
      let message = t('Could not import the structured question template.')
      if (importError instanceof StructuredQuestionTemplateError) {
        let localizedMessage: string
        if (importError.message.startsWith('Missing required columns:')) {
          localizedMessage = `${t('Missing required columns')}: ${importError.message.split(':').slice(1).join(':').trim()}`
        } else if (importError.message.startsWith('Question numbers must be unique')) {
          localizedMessage = `${t('Question numbers must be unique in the structured template')}: ${importError.message.split(':').slice(1).join(':').trim()}`
        } else if (importError.message.startsWith('Parent question ')) {
          localizedMessage = t('A referenced parent question was not found in the template.')
        } else {
          localizedMessage = t(importError.message)
        }
        message = `${importError.rowNumber ? `${t('Row')} ${importError.rowNumber}: ` : ''}${localizedMessage}`
      }
      setError(message)
    }
  }

  function importPastedQuestionText(): void {
    setError(null)
    setNotice(null)
    try {
      const rows = parsePastedQuestions(pastedQuestionsText)
      replaceVisibleDraftWithRows(rows)
      setPastedQuestionsText('')
      setNotice(t(
        preparationMode === 'structured_template'
          ? 'Pasted questions imported. Review every question before saving.'
          : 'The automatic draft was replaced with the pasted question list. Review it before saving.',
      ))
    } catch (importError) {
      const message =
        importError instanceof StructuredQuestionTemplateError
          ? t(importError.message)
          : t('Could not import the pasted questions.')
      setError(message)
    }
  }


  useEffect(() => {
    document.body.dataset.unsavedExtractionReview = String(isDirty)
    const warnBeforeUnload = (event: BeforeUnloadEvent): void => {
      if (!isDirty) return
      event.preventDefault()
    }
    window.addEventListener('beforeunload', warnBeforeUnload)
    return () => {
      delete document.body.dataset.unsavedExtractionReview
      window.removeEventListener('beforeunload', warnBeforeUnload)
    }
  }, [isDirty])

  if (isLoading) {
    return (
      <PageState
        state="loading"
        title={t('Loading extraction review')}
        message={t('Retrieving the immutable review revision and source anchors…')}
      />
    )
  }
  if (!review || !draft) {
    return (
      <PageState
        state="error"
        title={t('Could not load extraction review')}
        message={error ?? t('The extraction review is unavailable.')}
        action={
          <Button variant="secondary" onClick={() => void loadReview()}>
            {t('Retry review')}
          </Button>
        }
      />
    )
  }

  const tabs: TabItem<ReviewTab>[] = [
    {
      id: 'questions',
      label: t('{assessed} assessed questions + {containers} structural containers', {
        assessed: assessedQuestionCount,
        containers: structuralContainerCount,
      }),
    },
    { id: 'clos', label: `${t('CLOs')} (${draft.clos.length})` },
    { id: 'topics', label: `${t('Topics')} (${draft.topics.length})` },
    {
      id: 'structured',
      label: `${t('Supporting context')} (${(draft.supporting_materials ?? []).length}) · ${t('Explicit references')} (${(draft.document_references ?? []).length})`,
    },
  ]

  const sourceDocument: UploadedFileType =
    activeTab === 'clos' || activeTab === 'topics' ? 'tp153' : 'exam'

  function changeActiveTab(tab: ReviewTab): void {
    setActiveTab(tab)
    setSelectedQuestionId(null)
    setSelectedCourseRecord(null)
    if (tab === 'clos') {
      const first = draft.clos[0]
      setSelectedPage(first?.page_number ?? 1)
      setSelectedGeometry(first?.geometry ?? null)
    } else if (tab === 'topics') {
      const first = draft.topics[0]
      setSelectedPage(first?.page_number ?? 1)
      setSelectedGeometry(first?.geometry ?? null)
    } else {
      const first = draft.questions[0]
      setSelectedPage(first?.page_number ?? 1)
      setSelectedGeometry(first?.geometry ?? null)
      if (tab === 'questions' && first) setSelectedQuestionId(first.source_record_id)
    }
    setPdfFocusRequest((value) => value + 1)
  }

  function selectPdfLocation(
    pageNumber: number,
    geometry: ExtractionReviewQuestion['geometry'],
    questionSourceRecordId?: string,
  ): void {
    setSelectedPage(Math.max(1, pageNumber))
    setSelectedGeometry(geometry)
    setSelectedQuestionId(questionSourceRecordId ?? null)
    setSelectedCourseRecord(null)
    setPdfFocusRequest((value) => value + 1)
  }

  function selectCourseSpecificationLocation(
    collection: 'clos' | 'topics',
    id: string,
    pageNumber: number,
    geometry: ExtractionReviewClo['geometry'],
  ): void {
    setSelectedPage(Math.max(1, pageNumber))
    setSelectedGeometry(geometry)
    setSelectedQuestionId(null)
    setSelectedCourseRecord({ collection, id })
    setPdfFocusRequest((value) => value + 1)
  }

  function changePdfPage(pageNumber: number): void {
    setSelectedPage(Math.max(1, pageNumber))
    setSelectedGeometry(null)
    if (activeTab === 'questions') setSelectedQuestionId(null)
    setPdfFocusRequest((value) => value + 1)
  }

  function changeRecord(
    collection: EditableCollection,
    id: string,
    patch: Partial<ReviewRecord>,
  ): void {
    setNotice(null)
    setDraft((current) => {
      if (!current) return current
      const updated = updateSnapshotRecord(current, collection, id, patch)
      if (collection !== 'questions') return updated
      const question = updated.questions.find((item) => item.source_record_id === id)
      if (
        !question ||
        !isReviewerAddedQuestion(question)
      ) return updated
      return {
        ...updated,
        evidence: updated.evidence.map((item) =>
          item.question_source_record_id === id && item.evidence_type === 'question_text'
            ? {
                ...item,
                included: question.included,
                page_number: question.page_number,
                item_reference: question.number_label,
                extracted_text: question.question_text,
                geometry: question.geometry,
              }
            : item,
        ),
      }
    })
  }

  function addManualQuestion(pageNumber: number): string {
    const questionId = reviewRecordId()
    const evidenceId = reviewRecordId()
    setNotice(null)
    setError(null)
    setDraft((current) => {
      if (!current) return current
      const sequence = Math.max(-1, ...current.questions.map((item) => item.sequence)) + 1
      const question: ExtractionReviewQuestion = {
        source_record_id: questionId,
        included: true,
        parent_source_record_id: null,
        number_label: '',
        question_text: '',
        page_number: Math.max(1, pageNumber),
        marks: null,
        sequence,
        extraction_confidence: 1,
        geometry: null,
        question_type: 'unknown',
        instructions: null,
        extraction_method: 'manual_review',
        review_status: 'reviewed',
      }
      const evidence: ExtractionReviewEvidence = {
        source_record_id: evidenceId,
        included: true,
        question_source_record_id: questionId,
        source_document: 'exam',
        evidence_type: 'question_text',
        page_number: question.page_number,
        item_reference: '',
        extracted_text: '',
        extraction_confidence: 1,
        geometry: null,
      }
      return {
        ...current,
        questions: [...current.questions, question],
        evidence: [...current.evidence, evidence],
      }
    })
    setSelectedPage(Math.max(1, pageNumber))
    setSelectedGeometry(null)
    setSelectedQuestionId(questionId)
    setPdfFocusRequest((value) => value + 1)
    return questionId
  }

  function addManualClo(pageNumber: number): string {
    const id = reviewRecordId()
    const clo: ExtractionReviewClo = {
      source_record_id: id,
      included: true,
      code: '',
      text: '',
      program_outcome_reference: null,
      page_number: Math.max(1, pageNumber),
      extraction_confidence: 1,
      geometry: null,
    }
    setNotice(null)
    setError(null)
    setDraft((current) => current ? { ...current, clos: [...current.clos, clo] } : current)
    setSelectedPage(clo.page_number)
    setSelectedGeometry(null)
    setSelectedQuestionId(null)
    setSelectedCourseRecord({ collection: 'clos', id })
    setPdfFocusRequest((value) => value + 1)
    return id
  }

  function addManualTopic(pageNumber: number): string {
    const id = reviewRecordId()
    const topic: ExtractionReviewTopic = {
      source_record_id: id,
      included: true,
      code: null,
      text: '',
      expected_hours: null,
      page_number: Math.max(1, pageNumber),
      extraction_confidence: 1,
      geometry: null,
    }
    setNotice(null)
    setError(null)
    setDraft((current) => current ? { ...current, topics: [...current.topics, topic] } : current)
    setSelectedPage(topic.page_number)
    setSelectedGeometry(null)
    setSelectedQuestionId(null)
    setSelectedCourseRecord({ collection: 'topics', id })
    setPdfFocusRequest((value) => value + 1)
    return id
  }

  function splitQuestion(sourceRecordId: string): string {
    const createdId = reviewRecordId()
    const evidenceId = reviewRecordId()
    setNotice(null)
    setError(null)
    setDraft((current) => {
      if (!current) return current
      const source = current.questions.find((item) => item.source_record_id === sourceRecordId)
      if (!source) return current
      const sequence = Math.max(-1, ...current.questions.map((item) => item.sequence)) + 1
      const question: ExtractionReviewQuestion = {
        source_record_id: createdId,
        included: true,
        parent_source_record_id: source.parent_source_record_id,
        number_label: source.number_label ? `${source.number_label}b` : '',
        question_text: '',
        page_number: source.page_number,
        marks: null,
        sequence,
        extraction_confidence: 1,
        geometry: null,
        question_type: source.question_type ?? 'unknown',
        instructions: null,
        extraction_method: 'manual_review',
        review_status: 'reviewed',
      }
      const evidence: ExtractionReviewEvidence = {
        source_record_id: evidenceId,
        included: true,
        question_source_record_id: createdId,
        source_document: 'exam',
        evidence_type: 'question_text',
        page_number: source.page_number,
        item_reference: question.number_label,
        extracted_text: '',
        extraction_confidence: 1,
        geometry: null,
      }
      const sourceIndex = current.questions.findIndex(
        (item) => item.source_record_id === sourceRecordId,
      )
      const questions = [...current.questions]
      questions.splice(sourceIndex + 1, 0, question)
      return { ...current, questions, evidence: [...current.evidence, evidence] }
    })
    const source = draft?.questions.find((item) => item.source_record_id === sourceRecordId)
    if (source) {
      setSelectedPage(source.page_number)
      setSelectedGeometry(null)
    }
    setSelectedQuestionId(createdId)
    setPdfFocusRequest((value) => value + 1)
    return createdId
  }

  function mergeQuestionWithPrevious(sourceRecordId: string): string | null {
    if (!draft) return null
    const index = draft.questions.findIndex((item) => item.source_record_id === sourceRecordId)
    if (index < 0) return null
    const source = draft.questions[index]
    if (draft.questions.some(
      (item) => item.parent_source_record_id === source.source_record_id && item.included,
    )) {
      setError(t('A parent question with included child questions cannot be merged.'))
      return null
    }
    let previousIndex = index - 1
    while (
      previousIndex >= 0 &&
      (!draft.questions[previousIndex].included ||
        draft.questions[previousIndex].page_number !== source.page_number)
    ) {
      previousIndex -= 1
    }
    if (previousIndex < 0) {
      setError(t('No previous included question is available on this page.'))
      return null
    }
    const previous = draft.questions[previousIndex]
    if (draft.questions.some(
      (item) => item.parent_source_record_id === previous.source_record_id && item.included,
    )) {
      setError(t('A parent question with included child questions cannot be merged.'))
      return null
    }

    const mergedId = reviewRecordId()
    const evidenceId = reviewRecordId()
    setNotice(null)
    setError(null)
    setDraft((current) => {
      if (!current) return current
      const currentSource = current.questions.find(
        (item) => item.source_record_id === source.source_record_id,
      )
      const currentPrevious = current.questions.find(
        (item) => item.source_record_id === previous.source_record_id,
      )
      if (!currentSource || !currentPrevious) return current
      const combinedText = [currentPrevious.question_text.trim(), currentSource.question_text.trim()]
        .filter(Boolean)
        .join('\n')
      const combinedGeometry = unionGeometry([currentPrevious.geometry, currentSource.geometry])
      const combinedMarks =
        currentPrevious.marks !== null && currentSource.marks !== null
          ? currentPrevious.marks + currentSource.marks
          : currentPrevious.marks ?? currentSource.marks
      const mergedQuestion: ExtractionReviewQuestion = {
        source_record_id: mergedId,
        included: true,
        parent_source_record_id: currentPrevious.parent_source_record_id,
        number_label: currentPrevious.number_label,
        question_text: combinedText,
        page_number: currentPrevious.page_number,
        marks: combinedMarks,
        sequence: currentPrevious.sequence,
        extraction_confidence: 1,
        geometry: combinedGeometry,
        question_type:
          currentPrevious.question_type === currentSource.question_type
            ? currentPrevious.question_type
            : 'mixed',
        instructions: currentPrevious.instructions,
        extraction_method: 'manual_review',
        review_status: 'reviewed',
      }
      const mergedEvidence: ExtractionReviewEvidence = {
        source_record_id: evidenceId,
        included: true,
        question_source_record_id: mergedId,
        source_document: 'exam',
        evidence_type: 'question_text',
        page_number: mergedQuestion.page_number,
        item_reference: mergedQuestion.number_label,
        extracted_text: mergedQuestion.question_text,
        extraction_confidence: 1,
        geometry: mergedQuestion.geometry,
      }
      let updated = updateSnapshotRecord(current, 'questions', currentPrevious.source_record_id, {
        included: false,
      })
      updated = updateSnapshotRecord(updated, 'questions', currentSource.source_record_id, {
        included: false,
      })
      const insertionIndex = updated.questions.findIndex(
        (item) => item.source_record_id === currentPrevious.source_record_id,
      )
      const questions = [...updated.questions]
      questions.splice(Math.max(0, insertionIndex), 0, mergedQuestion)
      return {
        ...updated,
        questions,
        evidence: [...updated.evidence, mergedEvidence],
      }
    })
    setSelectedPage(previous.page_number)
    setSelectedGeometry(unionGeometry([previous.geometry, source.geometry]))
    setSelectedQuestionId(mergedId)
    setPdfFocusRequest((value) => value + 1)
    return mergedId
  }

  function removeManualQuestion(sourceRecordId: string): void {
    setNotice(null)
    setError(null)
    setDraft((current) => {
      if (!current) return current
      const source = current.questions.find((item) => item.source_record_id === sourceRecordId)
      if (!source || (!isManualQuestion(source) && !isPastedReviewQuestion(source))) return current
      return {
        ...current,
        questions: current.questions.filter((item) => item.source_record_id !== sourceRecordId),
        evidence: current.evidence.filter(
          (item) => item.question_source_record_id !== sourceRecordId,
        ),
        question_options: (current.question_options ?? []).filter(
          (item) => item.question_source_record_id !== sourceRecordId,
        ),
        question_blanks: (current.question_blanks ?? []).filter(
          (item) => item.question_source_record_id !== sourceRecordId,
        ),
        question_source_spans: (current.question_source_spans ?? []).filter(
          (item) => item.question_source_record_id !== sourceRecordId,
        ),
      }
    })
    if (selectedQuestionId === sourceRecordId) {
      setSelectedQuestionId(null)
      setSelectedGeometry(null)
    }
  }

  async function handleSave(): Promise<void> {
    if (!isDirty || !review || !draft) return
    if (hasIncompleteReviewRecords) {
      setError(t(hasIncompleteCourseSpecificationRecords
        ? 'Complete every added CLO or topic by entering its source-faithful text and selecting its Course Specification PDF region.'
        : preparationMode === 'structured_template'
          ? 'Complete every imported question by entering its number and text.'
          : 'Complete every added question by selecting its PDF region and entering its number and text.'))
      return
    }
    setIsSaving(true)
    setError(null)
    setNotice(null)
    try {
      const preparedDraft = withManualCourseSpecificationEvidence(
        draft,
        review.original_snapshot,
      )
      const saved = await saveExtractionReview(analysisId, review.revision_id, preparedDraft)
      setReview(saved)
      setDraft(cloneSnapshot(saved.snapshot))
      setNotice(`${t('Revision')} ${saved.revision_number} ${t('saved')}.`)
    } catch (saveError) {
      setError(localizeInterfaceError(saveError, locale, t, 'Could not save the extraction review.'))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleConfirm(): Promise<void> {
    if (!review || isDirty || !review.can_confirm) return
    setShowWarningConfirmation(false)
    setIsConfirming(true)
    setError(null)
    setNotice(null)
    try {
      const response = await confirmExtractionReview(analysisId, review.revision_id)
      onConfirmed(response)
    } catch (confirmError) {
      setError(localizeInterfaceError(
        confirmError,
        locale,
        t,
        'Could not confirm the extraction review.',
      ))
    } finally {
      setIsConfirming(false)
    }
  }

  function requestConfirmation(): void {
    if (!review || isDirty || !review.can_confirm || hasIncompleteReviewRecords) return
    void handleConfirm()
  }

  return (
    <div className="extraction-review-workspace">
      <Alert variant="info" title={t('Transcription review only')}>
        {t('Correct only what is visibly present in the uploaded Exam and Course Specification. Confirmation does not approve academic alignment and does not create missing official course information.')}
      </Alert>
      <MethodologyLink anchor="extraction-review" />

      <div className="review-summary-bar" aria-label={t('Extraction review revision status')}>
        <span>{t('Revision')} {review.revision_number}</span>
        <span>{isDirty ? t('Unsaved changes') : t('All changes saved')}</span>
        <span>{review.is_confirmed ? t('Confirmed') : t('Open for review')}</span>
        <span>{t('Extraction verification')}: {extractionVerificationLabel}</span>
      </div>

      <section className="review-faculty-summary" aria-labelledby="review-faculty-summary-title">
        <div>
          <h2 id="review-faculty-summary-title">{t('Review the extracted questions')}</h2>
          <div className="review-faculty-summary__counts">
            <span><strong>{assessedQuestionCount}</strong> {t('assessed questions')}</span>
            <span><strong>{structuralContainerCount}</strong> {t('structural containers')}</span>
            <span>{t('Ready for faculty review')}</span>
          </div>
          <p>{t('Review every extracted question against the PDF, correct anything that is incomplete or inaccurate, then confirm the extraction.')}</p>
        </div>
      </section>

      {false && preparationMode === 'structured_template' && (
        <section className="structured-template-import" aria-labelledby="structured-template-title">
          <div>
            <h2 id="structured-template-title">{t('Paste or import question list')}</h2>
            <p>{t('Paste questions copied from Word or PDF, or import the simple CSV. Only question number, text, and visible marks are required. Type and options are optional.')}</p>
          </div>
          <label className="structured-template-paste">
            <span>{t('Paste questions')}</span>
            <textarea
              dir="auto"
              rows={9}
              value={pastedQuestionsText}
              disabled={!review.can_edit}
              placeholder={t('Paste numbered questions here. Keep answer options on lines beginning with A, B, C, or D.')}
              onChange={(event) => setPastedQuestionsText(event.target.value)}
            />
          </label>
          <div className="structured-template-actions">
            <Button
              onClick={importPastedQuestionText}
              disabled={!review.can_edit || pastedQuestionsText.trim().length === 0}
            >
              {t('Import pasted questions')}
            </Button>
            <Button variant="secondary" onClick={downloadStructuredQuestionTemplate}>
              {t('Download simple CSV')}
            </Button>
            <label className="ui-button ui-button--secondary">
              {t('Import CSV')}
              <input
                className="visually-hidden"
                type="file"
                accept=".csv,text/csv"
                disabled={!review.can_edit}
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) void importStructuredTemplate(file)
                  event.target.value = ''
                }}
              />
            </label>
          </div>
        </section>
      )}
      {preparationMode === 'manual_pdf' && (
        <Alert variant="info" title={t('Manual visual question preparation')}>
          {t('No automatic questions are trusted in this mode. Select a page region, add the visible question, enter only the text shown in the PDF, and save the revision.') }
        </Alert>
      )}
      {preparationMode === 'assisted_pdf' && (
        <>
          <Alert variant="info" title={t('Assisted PDF extraction')}>
            {t('Automatic extraction is a proposal only. Review every question against the PDF and correct only what differs from the source.') }
          </Alert>
          <p className="review-copy-tip">
            <strong>{t('Copy from PDF')}:</strong>{' '}
            {t('Use Copy text in the PDF pane, select any text you need, then paste it exactly where you want inside an editable field.') }
          </p>
        </>
      )}

      {false && preparationMode === 'assisted_pdf' && (
        <section className="review-start-over" aria-labelledby="review-start-over-title">
          <div className="review-start-over__heading">
            <div>
              <h2 id="review-start-over-title">{t('Keep the automatic draft or start over')}</h2>
              <p>{t('Usually, keep the extracted questions and correct only what is missing. If the draft is not useful, you can replace the visible question list with questions pasted from the original PDF or with the simple CSV.')}</p>
            </div>
            <Button
              variant="secondary"
              disabled={!review.can_edit}
              onClick={() => setShowStartOverTools((value) => !value)}
            >
              {t(showStartOverTools ? 'Cancel start over' : 'Start over / paste questions')}
            </Button>
          </div>
          <p className="review-copy-tip">
            <strong>{t('For small corrections')}:</strong>{' '}
            {t('Use Copy text in the PDF pane, copy only the missing words, and paste them exactly where you want inside any editable field. You do not need to start over.')}
          </p>
          {showStartOverTools && (
            <div className="review-start-over__panel">
              <Alert variant="warning" title={t('Replace the visible automatic draft')}>
                {t('Importing here will exclude the current automatic questions from the working revision and replace them with the pasted or imported list. The original machine records remain preserved for audit until you save.')}
              </Alert>
              <label className="structured-template-paste">
                <span>{t('Paste questions')}</span>
                <textarea
                  dir="auto"
                  rows={10}
                  value={pastedQuestionsText}
                  disabled={!review.can_edit}
                  placeholder={t('Paste numbered questions here. Keep answer options on lines beginning with A, B, C, or D.')}
                  onChange={(event) => setPastedQuestionsText(event.target.value)}
                />
              </label>
              <div className="structured-template-actions">
                <Button
                  onClick={importPastedQuestionText}
                  disabled={!review.can_edit || pastedQuestionsText.trim().length === 0}
                >
                  {t('Replace draft with pasted questions')}
                </Button>
                <Button variant="secondary" onClick={downloadStructuredQuestionTemplate}>
                  {t('Download simple CSV')}
                </Button>
                <label className="ui-button ui-button--secondary">
                  {t('Replace draft from CSV')}
                  <input
                    className="visually-hidden"
                    type="file"
                    accept=".csv,text/csv"
                    disabled={!review.can_edit}
                    onChange={(event) => {
                      const file = event.target.files?.[0]
                      if (file) void importStructuredTemplate(file)
                      event.target.value = ''
                    }}
                  />
                </label>
              </div>
            </div>
          )}
        </section>
      )}

      {includedQuestionCount === 0 && preparationMode === 'assisted_pdf' && (
        <Alert variant="error" title={t('Exam extraction needs another attempt')}>
          {t('No reliable questions were extracted automatically. Add the visible question regions from the original PDF, rerun extraction, or replace the exam file.')}
        </Alert>
      )}
      {includedQuestionCount === 0 && preparationMode === 'structured_template' && (
        <Alert variant="warning" title={t('Paste or import questions to continue')}>
          {t('Paste questions copied from Word or import the simple CSV to continue.')}
        </Alert>
      )}

      {review.confirmation_blockers.length > 0 && (
        <Alert variant="error" title={t('Confirmation unavailable')}>
          <ul className="review-warning-list">
            {review.confirmation_blockers.map((blocker) => (
              <li key={blocker}>
                {localizeServerMessage(blocker, locale, t, 'Confirmation unavailable')}
              </li>
            ))}
          </ul>
        </Alert>
      )}
      {false && (extractionWarningGroups.length > 0 || groupedReviewWarnings.length > 0) && (
        <details className="review-technical-diagnostics">
          <summary>
            {t('Technical extraction details')} ({technicalWarningCount})
          </summary>
          <p>{t('These records are grouped by type and page for audit. Review recommendations do not block confirmation unless listed above.')}</p>
          {extractionWarningGroups.map((group) => {
            const first = group.items[0]
            const blockingIds = new Set(review.blocking_extraction_warning_ids ?? [])
            const isBlocking = group.items.some((item) => blockingIds.has(item.source_record_id))
            const allResolved = group.items.every((item) => item.resolved)
            return (
              <details
                className={`review-reconciliation-warning${isBlocking ? ' review-reconciliation-warning--critical' : ''}`}
                key={group.key}
              >
                <summary>
                  <strong><bdi>{group.code}</bdi></strong>
                  <span>
                    {group.pageNumber ? `${t('Page')} ${group.pageNumber} · ` : ''}
                    {group.items.length} {t(group.items.length === 1 ? 'record' : 'records')}
                  </span>
                </summary>
                <p>{localizeServerMessage(first.message, locale, t, group.code)}</p>
                {group.pageNumber && (
                  <Button variant="ghost" onClick={() => selectPdfLocation(group.pageNumber!, first.geometry)}>
                    {t('Show in PDF')}
                  </Button>
                )}
                {isBlocking && (
                  <label>
                    <input
                      type="checkbox"
                      checked={allResolved}
                      disabled={!review.can_edit}
                      onChange={(event) => {
                        const ids = new Set(group.items.map((item) => item.source_record_id))
                        setDraft((current) => current ? {
                          ...current,
                          extraction_warnings: (current.extraction_warnings ?? []).map((item) =>
                            ids.has(item.source_record_id)
                              ? { ...item, resolved: event.target.checked }
                              : item,
                          ),
                        } : current)
                      }}
                    />
                    {t('Resolve all warnings in this group')}
                  </label>
                )}
              </details>
            )
          })}
          {groupedReviewWarnings.length > 0 && (
            <ul className="review-warning-list">
              {groupedReviewWarnings.map((warning) => (
                <li key={`${warning.code}-${warning.message}`}>
                  {warning.count > 1 ? <strong>{warning.count}× </strong> : null}
                  {localizeServerMessage(warning.message, locale, t, warning.code)}
                  {warning.questionLabels.length > 0 ? (
                    <span> ({warning.questionLabels.join(', ')})</span>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </details>
      )}
      {error && (
        <Alert variant="error" title={t('Review action failed')}>
          {error}
        </Alert>
      )}
      {notice && (
        <Alert variant="success" title={t('Review saved')}>
          {notice}
        </Alert>
      )}

      <div className="review-split-layout">
        <ExamPdfPreview
          analysisId={analysisId}
          sourceDocument={sourceDocument}
          pageNumber={selectedPage}
          geometry={selectedGeometry}
          onPageChange={changePdfPage}
          focusRequest={pdfFocusRequest}
          onGeometryChange={
            activeTab === 'questions' && selectedQuestionId && review.can_edit
              ? (geometry) => {
                  const selected = draft.questions.find(
                    (item) => item.source_record_id === selectedQuestionId,
                  )
                  changeRecord('questions', selectedQuestionId, {
                    geometry,
                    extraction_method: selected && isStructuredTemplateQuestion(selected)
                      ? 'structured_template'
                      : selected && isPastedReviewQuestion(selected)
                        ? 'pasted_review'
                        : selected && isManualQuestion(selected)
                          ? 'manual_review'
                          : 'review_adjusted',
                  })
                  setSelectedGeometry(geometry)
                  setPdfFocusRequest((value) => value + 1)
                }
              : selectedCourseRecord && review.can_edit && (
                  selectedCourseRecord.collection === 'clos'
                    ? !review.original_snapshot.clos.some((item) => item.source_record_id === selectedCourseRecord.id)
                    : !review.original_snapshot.topics.some((item) => item.source_record_id === selectedCourseRecord.id)
                )
                ? (geometry) => {
                    changeRecord(selectedCourseRecord.collection, selectedCourseRecord.id, {
                      geometry,
                      page_number: selectedPage,
                      extraction_confidence: 1,
                    })
                    setSelectedGeometry(geometry)
                    setPdfFocusRequest((value) => value + 1)
                  }
                : undefined
          }
        />
        <div className="review-structured-pane">
          <Tabs
            items={tabs}
            value={activeTab}
            onValueChange={changeActiveTab}
            ariaLabel={t('Review Extraction')}
          />
          <section
            id={`tabpanel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`tab-${activeTab}`}
            className="review-tab-panel"
          >
        {(activeTab === 'clos' || activeTab === 'topics') && (
          <Alert variant="info" title={t('Review against the Course Specification PDF')}>
            {t('The Course Specification PDF is shown on the left. Use Copy text to copy exact wording. If a CLO or topic is missing, add a new record, paste or type only what appears in the PDF, then select its source area.')}
          </Alert>
        )}
        {activeTab === 'questions' && (
          <QuestionsPanel
            items={draft.questions}
            original={review.original_snapshot.questions}
            options={draft.question_options ?? []}
            originalOptions={review.original_snapshot.question_options ?? []}
            blanks={draft.question_blanks ?? []}
            originalBlanks={review.original_snapshot.question_blanks ?? []}
            sourceSpans={draft.question_source_spans ?? []}
            candidateEvidence={draft.evidence.filter((item) =>
              item.evidence_type.startsWith('extraction_candidate_'),
            )}
            supportingMaterials={draft.supporting_materials ?? []}
            preparationMode={preparationMode}
            disabled={!review.can_edit}
            onChange={(id, patch) => changeRecord('questions', id, patch)}
            onOptionChange={(id, patch) => changeRecord('question_options', id, patch)}
            onBlankChange={(id, patch) => changeRecord('question_blanks', id, patch)}
            onSelect={selectPdfLocation}
            selectedPage={selectedPage}
            onAddQuestion={addManualQuestion}
            onSplitQuestion={splitQuestion}
            onMergeQuestion={mergeQuestionWithPrevious}
            onRemoveManualQuestion={removeManualQuestion}
            reviewCuesByQuestion={questionReviewCuesByQuestion}
            requestedQuestionId={requestedReviewQuestionId}
          />
        )}
        {activeTab === 'clos' && (
          <ClosPanel
            items={draft.clos}
            original={review.original_snapshot.clos}
            disabled={!review.can_edit}
            selectedPage={selectedPage}
            onChange={(id, patch) => changeRecord('clos', id, patch)}
            onAdd={addManualClo}
            onSelect={(id, pageNumber, geometry) =>
              selectCourseSpecificationLocation('clos', id, pageNumber, geometry)
            }
          />
        )}
        {activeTab === 'topics' && (
          <TopicsPanel
            items={draft.topics}
            original={review.original_snapshot.topics}
            disabled={!review.can_edit}
            selectedPage={selectedPage}
            onChange={(id, patch) => changeRecord('topics', id, patch)}
            onAdd={addManualTopic}
            onSelect={(id, pageNumber, geometry) =>
              selectCourseSpecificationLocation('topics', id, pageNumber, geometry)
            }
          />
        )}
        {activeTab === 'structured' && (
          <StructuredEvidencePanel
            snapshot={draft}
            original={review.original_snapshot}
            disabled={!review.can_edit}
            onChange={changeRecord}
          />
        )}
          </section>
        </div>
      </div>

      {hasIncompleteReviewRecords && (
        <Alert variant="warning" title={t('Complete the added records before saving')}>
          {t(hasIncompleteCourseSpecificationRecords
            ? 'Each added CLO or topic needs editable source-faithful text and a selected region from the Course Specification PDF.'
            : preparationMode === 'structured_template'
              ? 'Each imported question needs a question number and editable source-faithful text.'
              : 'Each added question needs a question number, editable text, and a selected region from the original PDF.')}
        </Alert>
      )}

      {false && showWarningConfirmation && (
        <div className="review-confirm-backdrop" role="presentation">
          <section
            className="review-confirm-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-confirm-with-warnings-title"
          >
            <h2 id="review-confirm-with-warnings-title">{t('Continue with review recommendations?')}</h2>
            <p>
              {flaggedQuestionIds.length > 0
                ? `${flaggedQuestionIds.length} ${t(flaggedQuestionIds.length === 1 ? 'question has review recommendations.' : 'questions have review recommendations.')}`
                : t('Extraction review recommendations remain visible for audit.')}
            </p>
            <p>{t('You can continue to analysis now, or return to review them. These recommendations do not require a hidden acknowledgement checkbox.')}</p>
            <div className="review-confirm-dialog__actions">
              <Button
                variant="secondary"
                disabled={isConfirming}
                onClick={() => setShowWarningConfirmation(false)}
              >
                {t('Return to review')}
              </Button>
              <Button
                isLoading={isConfirming}
                loadingLabel={t('Confirming…')}
                onClick={() => void handleConfirm()}
              >
                {t('Continue to analysis')}
              </Button>
            </div>
          </section>
        </div>
      )}

      <div className="review-sticky-actions">
        <div>
          <strong>{isDirty ? t('Save this revision before confirming.') : t('Revision is saved.')}</strong>
          <p>{t('Confirmation permanently closes extraction editing for this analysis.')}</p>
        </div>
        <div className="review-action-buttons">
          <Button
            variant="secondary"
            disabled={!review.can_edit || !isDirty || hasIncompleteReviewRecords}
            isLoading={isSaving}
            loadingLabel={t('Saving revision…')}
            onClick={() => void handleSave()}
          >
            {t('Save New Revision')}
          </Button>
          <Button
            disabled={!review.can_confirm || isDirty || hasIncompleteReviewRecords}
            isLoading={isConfirming}
            loadingLabel={t('Confirming…')}
            onClick={requestConfirmation}
          >
            {t('Confirm Extraction and Continue')}
          </Button>
        </div>
      </div>
    </div>
  )
}
