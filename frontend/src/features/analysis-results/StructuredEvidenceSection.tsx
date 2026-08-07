import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'
import {
  listDocumentReferences,
  listQuestions,
  listSupportingMaterialAnnotations,
  listSupportingMaterials,
} from '../../api/analyses'
import { Button } from '../../components/ui/Button'
import { Drawer } from '../../components/ui/Drawer'
import { Icon } from '../../components/ui/Icon'
import { PageState } from '../../components/ui/PageState'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import type {
  DocumentReferenceResponse,
  QuestionResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'
import { sortQuestionsForFaculty } from './facultyOrdering'
import {
  buildMaterialRelationship,
  buildPhysicalMaterials,
  type MaterialRelationshipResult,
  type MaterialRelationshipView,
  type PhysicalMaterialView,
} from './materialRelationships'
import { MethodologyLink } from './MethodologyLink'

interface StructuredData {
  materials: SupportingMaterialResponse[]
  annotations: SupportingMaterialAnnotationResponse[]
  references: DocumentReferenceResponse[]
  questions: QuestionResponse[]
}

export const RESULT_LABELS: Record<MaterialRelationshipResult, string> = {
  linked: 'Linked',
  missing: 'Missing reference',
  ambiguous: 'Ambiguous reference',
  nearby: 'Proximity-based link',
}

function materialName(
  item: PhysicalMaterialView,
  t: (key: string, variables?: Record<string, string | number>) => string,
): string {
  if (item.caption) return item.caption
  if (item.label) return item.label
  if (item.material.material_type === 'figure') {
    return t('Unlabelled figure or diagram')
  }
  if (item.material.material_type === 'table') return t('Unlabelled table')
  return t('Unlabelled code block')
}

function relationshipReason(
  relationship: MaterialRelationshipView,
  questionReference: string,
  t: (key: string, variables?: Record<string, string | number>) => string,
): string {
  switch (relationship.result) {
    case 'linked':
      return t(
        '{question} refers to {reference}, which matches one uniquely labelled material.',
        {
          question: questionReference,
          reference: relationship.reference.target_label,
        },
      )
    case 'missing':
      return t(
        '{question} refers to {reference}, but no matching material was found.',
        {
          question: questionReference,
          reference: relationship.reference.target_label,
        },
      )
    case 'ambiguous':
      return t(
        '{question} refers to {reference}, but {count} distinct materials use that label.',
        {
          question: questionReference,
          reference: relationship.reference.target_label,
          count: relationship.exactCandidates.length,
        },
      )
    case 'nearby':
      return t(
        '{question} uses an implicit nearby reference. The nearby material is shown for review but is not an official uniquely labelled mapping.',
        { question: questionReference },
      )
  }
}

function candidatePages(relationship: MaterialRelationshipView): string {
  const candidates =
    relationship.result === 'ambiguous'
      ? relationship.exactCandidates
      : relationship.matchedMaterial
        ? [relationship.matchedMaterial]
        : []
  const pages = [
    ...new Set(candidates.map((candidate) => candidate.material.page_number)),
  ]
  return pages.length > 0 ? pages.join(', ') : '—'
}

type MaterialDrawerSelection =
  | {
      kind: 'reference'
      relationship: MaterialRelationshipView
      question: QuestionResponse | undefined
    }
  | {
      kind: 'direct'
      material: PhysicalMaterialView
      question: QuestionResponse | undefined
    }

function MaterialRelationshipDrawer({
  selection,
  onClose,
  returnFocusRef,
}: {
  selection: MaterialDrawerSelection | null
  onClose: () => void
  returnFocusRef: RefObject<HTMLElement | null>
}) {
  const { t } = useI18n()
  const question = selection?.question
  const questionReference = question?.number_label ?? t('Unknown question')

  return (
    <Drawer
      isOpen={selection !== null}
      onClose={onClose}
      titleId="material-relationship-details-title"
      returnFocusRef={returnFocusRef}
      scrollKey={
        selection?.kind === 'reference'
          ? selection.relationship.reference.id
          : selection?.material.material.id
      }
      title={
        <>
          {t('Materials & References')} · <bdi>{questionReference}</bdi>
        </>
      }
    >
      {selection?.kind === 'reference' && (() => {
        const { relationship } = selection
        const candidates =
          relationship.result === 'ambiguous'
            ? relationship.exactCandidates
            : relationship.matchedMaterial
              ? [relationship.matchedMaterial]
              : []
        return (
          <>
            <section className="ui-drawer-section material-drawer-card">
              <h3>{t('Question text')}</h3>
              <p dir="auto">
                {question?.question_text ?? t('Question text is unavailable.')}
              </p>
            </section>
            <section className="ui-drawer-section material-drawer-card">
              <h3>{t('Original reference phrase')}</h3>
              <p dir="auto"><bdi dir="auto">{relationship.reference.original_text}</bdi></p>
            </section>
            <section className="ui-drawer-section">
              <h3>
                {relationship.result === 'ambiguous'
                  ? t('Candidate materials')
                  : t('Matched material')}
              </h3>
              {candidates.length > 0 ? (
                <ul className="drawer-finding-list">
                  {candidates.map((candidate) => (
                    <li key={candidate.material.id} className="drawer-finding-item">
                      <strong dir="auto">{materialName(candidate, t)}</strong>
                      <p>{t('Page')}: {candidate.material.page_number}</p>
                      {candidate.material.source_text.trim() &&
                        candidate.material.source_text.trim() !== materialName(candidate, t).trim() && (
                          <p dir="auto"><bdi dir="auto">{candidate.material.source_text}</bdi></p>
                        )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{t('None')}</p>
              )}
            </section>
            <section className="ui-drawer-section material-drawer-card">
              <h3>{t('Relationship reason')}</h3>
              <p dir="auto">{relationshipReason(relationship, questionReference, t)}</p>
            </section>
            <dl className="material-reference-metadata material-drawer-metadata-card">
              <div>
                <dt>{t('Relationship result')}</dt>
                <dd>
                  <span
                    className="material-relationship-status"
                    data-relationship-result={relationship.result}
                  >
                    {t(RESULT_LABELS[relationship.result])}
                  </span>
                </dd>
              </div>
              <div>
                <dt>{t('Reference type')}</dt>
                <dd>{t(relationship.result === 'nearby' ? 'Implicit nearby reference' : 'Explicit labelled reference')}</dd>
              </div>
              <div>
                <dt>{t('Reference identity')}</dt>
                <dd dir="auto">
                  {t(relationship.reference.target_type.replace('_', ' '))}:{' '}
                  <bdi dir="auto">{relationship.reference.target_label}</bdi>
                </dd>
              </div>
            </dl>
          </>
        )
      })()}

      {selection?.kind === 'direct' && (
        <>
          <section className="ui-drawer-section material-drawer-card">
            <h3>{t('Question text')}</h3>
            <p dir="auto">{question?.question_text ?? t('Question text is unavailable.')}</p>
          </section>
          <section className="ui-drawer-section material-drawer-card">
            <h3>{t('Matched material')}</h3>
            <p dir="auto"><strong>{materialName(selection.material, t)}</strong></p>
            {selection.material.material.source_text.trim() &&
              selection.material.material.source_text.trim() !== materialName(selection.material, t).trim() && (
                <p dir="auto"><bdi dir="auto">{selection.material.material.source_text}</bdi></p>
              )}
          </section>
          <section className="ui-drawer-section material-drawer-card">
            <h3>{t('Relationship reason')}</h3>
            <p>{t('This supporting context is directly associated with the confirmed question evidence.')}</p>
          </section>
          <dl className="material-reference-metadata material-drawer-metadata-card">
            <div>
              <dt>{t('Relationship result')}</dt>
              <dd><span className="material-relationship-status" data-relationship-result="linked">{t('Linked')}</span></dd>
            </div>
            <div>
              <dt>{t('Page')}</dt>
              <dd>{selection.material.material.page_number}</dd>
            </div>
          </dl>
        </>
      )}
    </Drawer>
  )
}


export function StructuredEvidenceSection({ analysisId }: { analysisId: string }) {
  const { locale, t } = useI18n()
  const [retryNonce, setRetryNonce] = useState(0)
  const [drawerSelection, setDrawerSelection] = useState<MaterialDrawerSelection | null>(null)
  const activeDetailsTriggerRef = useRef<HTMLElement | null>(null)
  const requestKey = `${analysisId}:${locale}:${retryNonce}`
  const [loadState, setLoadState] = useState<{
    requestKey: string
    data: StructuredData | null
    error: string | null
  }>({ requestKey: '', data: null, error: null })
  const data = loadState.requestKey === requestKey ? loadState.data : null
  const error = loadState.requestKey === requestKey ? loadState.error : null

  useEffect(() => {
    let cancelled = false
    Promise.all([
      listSupportingMaterials(analysisId),
      listSupportingMaterialAnnotations(analysisId),
      listDocumentReferences(analysisId),
      listQuestions(analysisId),
    ])
      .then(([materials, annotations, references, questions]) => {
        if (!cancelled) {
          setLoadState({
            requestKey,
            data: { materials, annotations, references, questions },
            error: null,
          })
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setLoadState({
            requestKey,
            data: null,
            error: localizeInterfaceError(
              loadError,
              locale,
              t,
              'Could not load supporting-material evidence.',
            ),
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [analysisId, locale, requestKey, retryNonce, t])

  const presentation = useMemo(() => {
    if (!data) return null
    const materials = buildPhysicalMaterials(data.materials, data.annotations)
    const questionOrder = sortQuestionsForFaculty(data.questions)
    const questionIndex = new Map(
      questionOrder.map((question, index) => [question.id, index]),
    )
    const references = data.references
      .filter((reference) => reference.target_type !== 'question')
      .sort(
        (left, right) =>
          (questionIndex.get(left.question_id ?? '') ?? Number.MAX_SAFE_INTEGER) -
            (questionIndex.get(right.question_id ?? '') ?? Number.MAX_SAFE_INTEGER) ||
          left.page_number - right.page_number ||
          left.created_at.localeCompare(right.created_at),
      )
      .map((reference) => buildMaterialRelationship(reference, materials))
    const directMaterials = materials
      .filter((item) => item.material.question_id !== null)
      .sort(
        (left, right) =>
          (questionIndex.get(left.material.question_id ?? '') ?? Number.MAX_SAFE_INTEGER) -
            (questionIndex.get(right.material.question_id ?? '') ?? Number.MAX_SAFE_INTEGER) ||
          left.material.page_number - right.material.page_number,
      )
    const referencedMaterialIds = new Set(
      references.flatMap((relationship) => [
        ...relationship.exactCandidates.map((candidate) => candidate.material.id),
        ...relationship.nearbyCandidates.map((candidate) => candidate.material.id),
      ]),
    )
    return {
      materials,
      directMaterials: directMaterials.filter(
        (item) => !referencedMaterialIds.has(item.material.id),
      ),
      references,
      questionsById: new Map(
        data.questions.map((question) => [question.id, question]),
      ),
      questionIndex,
    }
  }, [data])

  if (error) {
    return (
      <PageState
        state="error"
        title={t('Could not load supporting-material evidence')}
        message={error}
        action={
          <Button variant="secondary" onClick={() => setRetryNonce((value) => value + 1)}>
            {t('Try again')}
          </Button>
        }
      />
    )
  }
  if (!data || !presentation) {
    return (
      <PageState
        state="loading"
        title={t('Loading supporting-material evidence')}
        message={t(
          'Retrieving figures, tables, code blocks, and explicit references…',
        )}
      />
    )
  }
  if (
    presentation.materials.length === 0 &&
    presentation.references.length === 0 &&
    presentation.directMaterials.length === 0
  ) {
    return (
      <PageState
        state="empty"
        title={t('No structured supporting material')}
        message={t(
          'No figures, tables, code blocks, or explicit references were extracted.',
        )}
      />
    )
  }

  return (
    <div className="results-section-stack structured-evidence-section">
      <div className="results-section-heading">
        <div>
          <h2>{t('Materials & References')}</h2>
          <p>
            {t('Review how each question is linked to the supporting figures, tables, diagrams, or code identified in the exam.')}
          </p>
          <MethodologyLink anchor="evidence-traceability" />
        </div>
      </div>

      {(presentation.references.length > 0 || presentation.directMaterials.length > 0) ? (
        <ResponsiveTable
          caption={t('Question-to-material relationships')}
          className="academic-summary-table material-relationships-table"
        >
          <thead>
            <tr>
              <th scope="col">{t('Question')}</th>
              <th scope="col">{t('Referenced item')}</th>
              <th scope="col">{t('Matched material')}</th>
              <th scope="col">{t('Relationship result')}</th>
              <th scope="col">{t('Page')}</th>
              <th scope="col">{t('Details')}</th>
            </tr>
          </thead>
          <tbody>
            {[
              ...presentation.references.map((relationship) => ({
                kind: 'reference' as const,
                sortQuestionId: relationship.reference.question_id,
                sortPage: relationship.reference.page_number,
                id: relationship.reference.id,
                relationship,
              })),
              ...presentation.directMaterials.map((material) => ({
                kind: 'direct' as const,
                sortQuestionId: material.material.question_id,
                sortPage: material.material.page_number,
                id: `direct-${material.material.id}`,
                material,
              })),
            ]
              .sort((left, right) =>
                (presentation.questionIndex.get(left.sortQuestionId ?? '') ?? Number.MAX_SAFE_INTEGER) -
                  (presentation.questionIndex.get(right.sortQuestionId ?? '') ?? Number.MAX_SAFE_INTEGER) ||
                left.sortPage - right.sortPage ||
                left.id.localeCompare(right.id),
              )
              .map((row) => {
                if (row.kind === 'reference') {
                  const relationship = row.relationship
                  const question = relationship.reference.question_id
                    ? presentation.questionsById.get(relationship.reference.question_id)
                    : undefined
                  const questionReference = question?.number_label ?? t('Unknown question')
                  const matchedText =
                    relationship.result === 'ambiguous'
                      ? t('{count} possible matches', { count: relationship.exactCandidates.length })
                      : relationship.matchedMaterial
                        ? materialName(relationship.matchedMaterial, t)
                        : t('None')
                  return (
                    <tr key={row.id}>
                      <th scope="row" data-label={t('Question')}><bdi>{questionReference}</bdi></th>
                      <td data-label={t('Referenced item')} dir="auto"><bdi dir="auto">{relationship.reference.original_text}</bdi></td>
                      <td data-label={t('Matched material')} dir="auto">{matchedText}</td>
                      <td data-label={t('Relationship result')}>
                        <span className="material-relationship-status" data-relationship-result={relationship.result}>
                          {t(RESULT_LABELS[relationship.result])}
                        </span>
                      </td>
                      <td data-label={t('Page')}><bdi>{candidatePages(relationship)}</bdi></td>
                      <td data-label={t('Details')}>
                        <button
                          type="button"
                          className="details-icon-action"
                          aria-label={t('View details')}
                          title={t('View details')}
                          onClick={(event) => {
                            activeDetailsTriggerRef.current = event.currentTarget
                            setDrawerSelection({ kind: 'reference', relationship, question })
                          }}
                        >
                          <Icon name="eye" />
                        </button>
                      </td>
                    </tr>
                  )
                }

                const item = row.material
                const question = item.material.question_id
                  ? presentation.questionsById.get(item.material.question_id)
                  : undefined
                return (
                  <tr key={row.id}>
                    <th scope="row" data-label={t('Question')}><bdi>{question?.number_label ?? t('Unknown question')}</bdi></th>
                    <td data-label={t('Referenced item')}>—</td>
                    <td data-label={t('Matched material')} dir="auto">{materialName(item, t)}</td>
                    <td data-label={t('Relationship result')}>
                      <span className="material-relationship-status" data-relationship-result="linked">{t('Linked')}</span>
                    </td>
                    <td data-label={t('Page')}><bdi>{item.material.page_number}</bdi></td>
                    <td data-label={t('Details')}>
                      <button
                        type="button"
                        className="details-icon-action"
                        aria-label={t('View details')}
                        title={t('View details')}
                        onClick={(event) => {
                          activeDetailsTriggerRef.current = event.currentTarget
                          setDrawerSelection({ kind: 'direct', material: item, question })
                        }}
                      >
                        <Icon name="eye" />
                      </button>
                    </td>
                  </tr>
                )
              })}
          </tbody>
        </ResponsiveTable>
      ) : (
        <p className="results-empty-state">
          {t('No confirmed question-to-context links were identified.')}
        </p>
      )}

      <MaterialRelationshipDrawer
        selection={drawerSelection}
        onClose={() => setDrawerSelection(null)}
        returnFocusRef={activeDetailsTriggerRef}
      />
    </div>
  )
}
