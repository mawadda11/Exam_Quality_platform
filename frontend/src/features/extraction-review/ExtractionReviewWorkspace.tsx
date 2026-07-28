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
  ExtractionReviewQuestion,
  ExtractionReviewResponse,
  ExtractionReviewSnapshot,
  ExtractionReviewTopic,
} from '../../types/api'

type ReviewTab = 'questions' | 'clos' | 'topics'
type EditableCollection = ReviewTab
type ReviewRecord = ExtractionReviewQuestion | ExtractionReviewClo | ExtractionReviewTopic

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


  const items = snapshot[collection] as ReviewRecord[]
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
  disabled,
  onChange,
}: {
  items: ExtractionReviewQuestion[]
  original: ExtractionReviewQuestion[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewQuestion>) => void
}) {
  const { t } = useI18n()
  if (!items.length) return <EmptyCollection label="Questions" />
  const originals = new Map(original.map((item) => [item.source_record_id, item]))
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

  return (
    <div className="review-record-list">
      {items.map((item) => {
        const children = childrenByParent.get(item.source_record_id) ?? []
        const isContainer = children.length > 0
        const childMarks = children.reduce((total, child) => total + (child.marks ?? 0), 0)
        return (
          <Card
            as="article"
            className={`${!item.included ? 'review-record review-record--excluded' : 'review-record'}${isContainer ? ' review-record--container' : ''}`}
            key={item.source_record_id}
            style={{ '--question-depth': depth(item) } as CSSProperties}
          >
            <RecordHeader
              title={item.number_label}
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
            {isContainer && (
              <Alert variant="info" title={t('Parent / Container Question')}>
                <p>{t('This structural question groups the sub-questions below and is not scored as an independent semantic item.')}</p>
                <p>{t('Sub-question marks total')}: <strong>{childMarks}</strong></p>
              </Alert>
            )}
            <div className="review-form-grid">
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
                {t('Marks')}
                <input
                  type="number"
                  min="0"
                  step="any"
                  value={item.marks ?? ''}
                  disabled={disabled || !item.included || isContainer}
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
                  value={item.question_text}
                  disabled={disabled || !item.included}
                  onChange={(event) =>
                    onChange(item.source_record_id, { question_text: event.target.value })
                  }
                />
              </label>
            </div>
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
  onChange,
}: {
  items: ExtractionReviewClo[]
  original: ExtractionReviewClo[]
  disabled: boolean
  onChange: (id: string, patch: Partial<ExtractionReviewClo>) => void
}) {
  const { t } = useI18n()
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
  const { t } = useI18n()
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
    { id: 'questions', label: `${t('Questions')} (${draft.questions.length})` },
    { id: 'clos', label: `${t('CLOs')} (${draft.clos.length})` },
    { id: 'topics', label: `${t('Topics')} (${draft.topics.length})` },
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
      setNotice(`${t('Revision')} ${saved.revision_number} ${t('saved')}.`)
    } catch (saveError) {
      setError(localizeInterfaceError(saveError, locale, t, 'Could not save the extraction review.'))
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

  return (
    <div className="extraction-review-workspace">
      <Alert variant="info" title={t('Transcription review only')}>
        {t('Correct only what is visibly present in the uploaded Exam and TP-153. Confirmation does not approve academic alignment and does not create missing official course information.')}
      </Alert>

      <div className="review-summary-bar" aria-label={t('Extraction review revision status')}>
        <span>{t('Revision')} {review.revision_number}</span>
        <span>{isDirty ? t('Unsaved changes') : t('All changes saved')}</span>
        <span>{review.is_confirmed ? t('Confirmed') : t('Open for review')}</span>
      </div>

      {review.warnings.length > 0 && (
        <Alert variant="warning" title={t('Items requiring attention')}>
          <ul className="review-warning-list">
            {review.warnings.map((warning, index) => (
              <li key={`${warning.code}-${warning.source_record_id ?? 'collection'}-${index}`}>
                {localizeServerMessage(
                  warning.message,
                  locale,
                  t,
                  'Items requiring attention',
                )}
              </li>
            ))}
          </ul>
        </Alert>
      )}
      {review.confirmation_blockers.map((blocker) => (
        <Alert variant="warning" title={t('Confirmation unavailable')} key={blocker}>
          {localizeServerMessage(blocker, locale, t, 'Confirmation unavailable')}
        </Alert>
      ))}
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

      <Tabs
        items={tabs}
        value={activeTab}
        onValueChange={setActiveTab}
        ariaLabel={t('Review Extraction')}
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
      </section>

      <div className="review-sticky-actions">
        <div>
          <strong>{isDirty ? t('Save this revision before confirming.') : t('Revision is saved.')}</strong>
          <p>{t('Confirmation permanently closes extraction editing for this analysis.')}</p>
        </div>
        <div className="review-action-buttons">
          <Button
            variant="secondary"
            disabled={!review.can_edit || !isDirty}
            isLoading={isSaving}
            loadingLabel={t('Saving revision…')}
            onClick={() => void handleSave()}
          >
            {t('Save New Revision')}
          </Button>
          <Button
            disabled={!review.can_confirm || isDirty}
            isLoading={isConfirming}
            loadingLabel={t('Confirming…')}
            onClick={() => void handleConfirm()}
          >
            {t('Confirm Extraction and Continue')}
          </Button>
        </div>
      </div>
    </div>
  )
}
