import { useEffect, useMemo, useState } from 'react'
import {
  confirmExtractionReview,
  getExtractionReview,
  saveExtractionReview,
} from '../../api/analyses'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { PageState } from '../../components/ui/PageState'
import { Tabs, type TabItem } from '../../components/ui/Tabs'
import type {
  ExtractionReviewAssessmentRecord,
  ExtractionReviewClo,
  ExtractionReviewConfirmResponse,
  ExtractionReviewEvidence,
  ExtractionReviewQuestion,
  ExtractionReviewResponse,
  ExtractionReviewSnapshot,
  ExtractionReviewTopic,
} from '../../types/api'

type ReviewTab = 'questions' | 'clos' | 'topics' | 'assessment_records' | 'evidence'
type EditableCollection = ReviewTab
type ReviewRecord =
  | ExtractionReviewQuestion
  | ExtractionReviewClo
  | ExtractionReviewTopic
  | ExtractionReviewAssessmentRecord
  | ExtractionReviewEvidence

interface ExtractionReviewWorkspaceProps {
  analysisId: string
  onConfirmed: (response: ExtractionReviewConfirmResponse) => void
}

function cloneSnapshot(snapshot: ExtractionReviewSnapshot): ExtractionReviewSnapshot {
  return JSON.parse(JSON.stringify(snapshot)) as ExtractionReviewSnapshot
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

  if (collection === 'evidence' && patch.included === true) {
    const evidence = snapshot.evidence.find((item) => item.source_record_id === sourceRecordId)
    const questionId = evidence?.question_source_record_id
    if (questionId) {
      const includedIds = questionAncestors(snapshot.questions, questionId)
      return {
        ...snapshot,
        questions: snapshot.questions.map((question) =>
          includedIds.has(question.source_record_id)
            ? { ...question, included: true }
            : question,
        ),
        evidence: replaceRecord<ExtractionReviewEvidence>(
          snapshot.evidence,
          sourceRecordId,
          patch as Partial<ExtractionReviewEvidence>,
        ),
      }
    }
  }

  const items = snapshot[collection] as ReviewRecord[]
  return {
    ...snapshot,
    [collection]: replaceRecord(items, sourceRecordId, patch),
  } as ExtractionReviewSnapshot
}

function confidenceLabel(value: number): string {
  return `${Math.round(value * 100)}% extraction confidence`
}

function optionalNumber(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

function RecordHeader({
  title,
  included,
  pageNumber,
  confidence,
  disabled,
  onIncludedChange,
  onRestore,
}: {
  title: string
  included: boolean
  pageNumber: number
  confidence: number
  disabled: boolean
  onIncludedChange: (included: boolean) => void
  onRestore: () => void
}) {
  return (
    <div className="review-record-header">
      <div>
        <h3>{title}</h3>
        <p className="review-source-anchor">
          Page {pageNumber} · {confidenceLabel(confidence)}
        </p>
      </div>
      <div className="review-record-controls">
        <label className="review-include-control">
          <input
            type="checkbox"
            checked={included}
            disabled={disabled}
            onChange={(event) => onIncludedChange(event.target.checked)}
          />
          Include in analysis
        </label>
        <Button variant="ghost" disabled={disabled} onClick={onRestore}>
          Restore machine value
        </Button>
      </div>
    </div>
  )
}

function EmptyCollection({ label }: { label: string }) {
  return (
    <PageState
      state="empty"
      title={`No ${label} extracted`}
      message="The empty collection is preserved as source evidence; do not create replacement official records here."
    />
  )
}

function QuestionsPanel({
  items,
  original,
  disabled,
  onChange,
}: {
  items: ExtractionReviewQuestion[]
  original: ExtractionReviewQuestion[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewQuestion>) => void
}) {
  if (!items.length) return <EmptyCollection label="questions" />
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={item.number_label}
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
          <div className="review-form-grid">
            <label>
              Question number
              <input
                value={item.number_label}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { number_label: event.target.value })
                }
              />
            </label>
            <label>
              Marks
              <input
                type="number"
                min="0"
                step="any"
                value={item.marks ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { marks: optionalNumber(event.target.value) })
                }
              />
            </label>
            <label className="review-field-wide">
              Question text
              <textarea
                rows={4}
                value={item.question_text}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { question_text: event.target.value })
                }
              />
            </label>
          </div>
        </Card>
      ))}
    </div>
  )
}

function ClosPanel({
  items,
  original,
  disabled,
  onChange,
}: {
  items: ExtractionReviewClo[]
  original: ExtractionReviewClo[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewClo>) => void
}) {
  if (!items.length) return <EmptyCollection label="CLOs" />
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={item.code}
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
          <div className="review-form-grid">
            <label>
              CLO code
              <input
                value={item.code}
                disabled={disabled || !item.included}
                onChange={(event) => onChange(item.source_record_id, { code: event.target.value })}
              />
            </label>
            <label>
              Program outcome reference
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
              CLO text
              <textarea
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
  onChange,
}: {
  items: ExtractionReviewTopic[]
  original: ExtractionReviewTopic[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewTopic>) => void
}) {
  if (!items.length) return <EmptyCollection label="topics" />
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={item.code ?? item.text.slice(0, 50)}
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
          <div className="review-form-grid">
            <label>
              Topic code
              <input
                value={item.code ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { code: event.target.value || null })
                }
              />
            </label>
            <label>
              Expected hours
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
              Topic text
              <textarea
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

function AssessmentPanel({
  items,
  original,
  disabled,
  onChange,
}: {
  items: ExtractionReviewAssessmentRecord[]
  original: ExtractionReviewAssessmentRecord[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewAssessmentRecord>) => void
}) {
  if (!items.length) return <EmptyCollection label="assessment records" />
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={item.method}
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
          <div className="review-form-grid">
            <label>
              Assessment method
              <input
                value={item.method}
                disabled={disabled || !item.included}
                onChange={(event) => onChange(item.source_record_id, { method: event.target.value })}
              />
            </label>
            <label>
              Percentage
              <input
                type="number"
                min="0"
                max="100"
                step="any"
                value={item.percentage ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, {
                    percentage: optionalNumber(event.target.value),
                  })
                }
              />
            </label>
            <label className="review-field-wide">
              Activity
              <input
                value={item.activity ?? ''}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { activity: event.target.value || null })
                }
              />
            </label>
          </div>
        </Card>
      ))}
    </div>
  )
}

function EvidencePanel({
  items,
  original,
  disabled,
  onChange,
}: {
  items: ExtractionReviewEvidence[]
  original: ExtractionReviewEvidence[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewEvidence>) => void
}) {
  if (!items.length) return <EmptyCollection label="evidence records" />
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
  return (
    <div className="review-record-list">
      {items.map((item) => (
        <Card as="article" className={!item.included ? 'review-record review-record--excluded' : 'review-record'} key={item.source_record_id}>
          <RecordHeader
            title={`${item.source_document.toUpperCase()} · ${item.evidence_type}`}
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
          <div className="review-form-grid">
            <label>
              Item reference
              <input
                value={item.item_reference}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { item_reference: event.target.value })
                }
              />
            </label>
            <label className="review-field-wide">
              Extracted text
              <textarea
                rows={4}
                value={item.extracted_text}
                disabled={disabled || !item.included}
                onChange={(event) =>
                  onChange(item.source_record_id, { extracted_text: event.target.value })
                }
              />
            </label>
          </div>
        </Card>
      ))}
    </div>
  )
}

export function ExtractionReviewWorkspace({
  analysisId,
  onConfirmed,
}: ExtractionReviewWorkspaceProps) {
  const [review, setReview] = useState<ExtractionReviewResponse | null>(null)
  const [draft, setDraft] = useState<ExtractionReviewSnapshot | null>(null)
  const [activeTab, setActiveTab] = useState<ReviewTab>('questions')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isConfirming, setIsConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  async function loadReview(): Promise<void> {
    setIsLoading(true)
    setError(null)
    try {
      const response = await getExtractionReview(analysisId)
      setReview(response)
      setDraft(cloneSnapshot(response.snapshot))
    } catch (loadError) {
      setError(
        loadError instanceof ApiError
          ? loadError.detail
          : 'Could not load the extraction review.',
      )
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
      })
      .catch((loadError: unknown) => {
        if (cancelled) return
        setError(
          loadError instanceof ApiError
            ? loadError.detail
            : 'Could not load the extraction review.',
        )
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [analysisId])

  const isDirty = useMemo(
    () => Boolean(review && draft && JSON.stringify(review.snapshot) !== JSON.stringify(draft)),
    [draft, review],
  )

  if (isLoading) {
    return (
      <PageState
        state="loading"
        title="Loading extraction review"
        message="Retrieving the immutable review revision and source anchors…"
      />
    )
  }
  if (!review || !draft) {
    return (
      <PageState
        state="error"
        title="Could not load extraction review"
        message={error ?? 'The extraction review is unavailable.'}
        action={
          <Button variant="secondary" onClick={() => void loadReview()}>
            Retry review
          </Button>
        }
      />
    )
  }

  const tabs: TabItem<ReviewTab>[] = [
    { id: 'questions', label: `Questions (${draft.questions.length})` },
    { id: 'clos', label: `CLOs (${draft.clos.length})` },
    { id: 'topics', label: `Topics (${draft.topics.length})` },
    {
      id: 'assessment_records',
      label: `Assessment (${draft.assessment_records.length})`,
    },
    { id: 'evidence', label: `Evidence (${draft.evidence.length})` },
  ]

  function changeRecord(
    collection: EditableCollection,
    id: string,
    patch: Partial<ReviewRecord>,
  ): void {
    setNotice(null)
    setDraft((current) =>
      current ? updateSnapshotRecord(current, collection, id, patch) : current,
    )
  }

  async function handleSave(): Promise<void> {
    if (!isDirty || !review || !draft) return
    setIsSaving(true)
    setError(null)
    setNotice(null)
    try {
      const saved = await saveExtractionReview(analysisId, review.revision_id, draft)
      setReview(saved)
      setDraft(cloneSnapshot(saved.snapshot))
      setNotice(`Revision ${saved.revision_number} saved.`)
    } catch (saveError) {
      setError(
        saveError instanceof ApiError
          ? saveError.detail
          : 'Could not save the extraction review.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function handleConfirm(): Promise<void> {
    if (!review || isDirty || !review.can_confirm) return
    setIsConfirming(true)
    setError(null)
    setNotice(null)
    try {
      const response = await confirmExtractionReview(analysisId, review.revision_id)
      onConfirmed(response)
    } catch (confirmError) {
      setError(
        confirmError instanceof ApiError
          ? confirmError.detail
          : 'Could not confirm the extraction review.',
      )
    } finally {
      setIsConfirming(false)
    }
  }

  return (
    <div className="extraction-review-workspace">
      <Alert variant="info" title="Transcription review only">
        Correct only what is visibly present in the uploaded Exam and TP-153. Confirmation does
        not approve academic alignment and does not create missing official course information.
      </Alert>

      <div className="review-summary-bar" aria-label="Extraction review revision status">
        <span>Revision {review.revision_number}</span>
        <span>{isDirty ? 'Unsaved changes' : 'All changes saved'}</span>
        <span>{review.is_confirmed ? 'Confirmed' : 'Open for review'}</span>
      </div>

      {review.warnings.length > 0 && (
        <Alert variant="warning" title="Items requiring attention">
          <ul className="review-warning-list">
            {review.warnings.map((warning, index) => (
              <li key={`${warning.code}-${warning.source_record_id ?? 'collection'}-${index}`}>
                {warning.message}
              </li>
            ))}
          </ul>
        </Alert>
      )}
      {review.confirmation_blockers.map((blocker) => (
        <Alert variant="warning" title="Confirmation unavailable" key={blocker}>
          {blocker}
        </Alert>
      ))}
      {error && (
        <Alert variant="error" title="Review action failed">
          {error}
        </Alert>
      )}
      {notice && (
        <Alert variant="success" title="Review saved">
          {notice}
        </Alert>
      )}

      <Tabs
        items={tabs}
        value={activeTab}
        onValueChange={setActiveTab}
        ariaLabel="Extraction review sections"
      />
      <section
        id={`tabpanel-${activeTab}`}
        role="tabpanel"
        aria-labelledby={`tab-${activeTab}`}
        className="review-tab-panel"
      >
        {activeTab === 'questions' && (
          <QuestionsPanel
            items={draft.questions}
            original={review.original_snapshot.questions}
            disabled={!review.can_edit}
            onChange={(id, patch) => changeRecord('questions', id, patch)}
          />
        )}
        {activeTab === 'clos' && (
          <ClosPanel
            items={draft.clos}
            original={review.original_snapshot.clos}
            disabled={!review.can_edit}
            onChange={(id, patch) => changeRecord('clos', id, patch)}
          />
        )}
        {activeTab === 'topics' && (
          <TopicsPanel
            items={draft.topics}
            original={review.original_snapshot.topics}
            disabled={!review.can_edit}
            onChange={(id, patch) => changeRecord('topics', id, patch)}
          />
        )}
        {activeTab === 'assessment_records' && (
          <AssessmentPanel
            items={draft.assessment_records}
            original={review.original_snapshot.assessment_records}
            disabled={!review.can_edit}
            onChange={(id, patch) => changeRecord('assessment_records', id, patch)}
          />
        )}
        {activeTab === 'evidence' && (
          <EvidencePanel
            items={draft.evidence}
            original={review.original_snapshot.evidence}
            disabled={!review.can_edit}
            onChange={(id, patch) => changeRecord('evidence', id, patch)}
          />
        )}
      </section>

      <div className="review-sticky-actions">
        <div>
          <strong>{isDirty ? 'Save this revision before confirming.' : 'Revision is saved.'}</strong>
          <p>Confirmation permanently closes extraction editing for this analysis.</p>
        </div>
        <div className="review-action-buttons">
          <Button
            variant="secondary"
            disabled={!review.can_edit || !isDirty}
            isLoading={isSaving}
            loadingLabel="Saving revision…"
            onClick={() => void handleSave()}
          >
            Save New Revision
          </Button>
          <Button
            disabled={!review.can_confirm || isDirty}
            isLoading={isConfirming}
            loadingLabel="Confirming…"
            onClick={() => void handleConfirm()}
          >
            Confirm Extraction and Continue
          </Button>
        </div>
      </div>
    </div>
  )
}
