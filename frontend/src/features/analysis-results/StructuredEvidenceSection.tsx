import { useEffect, useMemo, useState } from 'react'
import {
  listDocumentReferences,
  listQuestions,
  listSupportingMaterialAnnotations,
  listSupportingMaterials,
} from '../../api/analyses'
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

const RESULT_LABELS: Record<MaterialRelationshipResult, string> = {
  linked: 'Linked',
  missing: 'Missing reference',
  ambiguous: 'Ambiguous reference',
  nearby: 'Suggested nearby material',
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

function RelationshipDetails({
  relationship,
  question,
}: {
  relationship: MaterialRelationshipView
  question: QuestionResponse | undefined
}) {
  const { t } = useI18n()
  const questionReference = question?.number_label ?? t('Unknown question')
  const candidates =
    relationship.result === 'ambiguous'
      ? relationship.exactCandidates
      : relationship.matchedMaterial
        ? [relationship.matchedMaterial]
        : []

  return (
    <details className="material-relationship-details">
      <summary>{t('View details')}</summary>
      <div className="material-relationship-detail-grid">
        <section>
          <h4>{t('Question text')}</h4>
          <p dir="auto">
            {question?.question_text ?? t('Question text is unavailable.')}
          </p>
        </section>
        <section>
          <h4>{t('Original reference phrase')}</h4>
          <p dir="auto">
            <bdi dir="auto">{relationship.reference.original_text}</bdi>
          </p>
        </section>
        <section>
          <h4>
            {relationship.result === 'ambiguous'
              ? t('Candidate materials')
              : t('Matched material')}
          </h4>
          {candidates.length > 0 ? (
            <ul>
              {candidates.map((candidate) => (
                <li key={candidate.material.id}>
                  <span dir="auto">{materialName(candidate, t)}</span>
                  {' — '}
                  {t('page')} {candidate.material.page_number}
                </li>
              ))}
            </ul>
          ) : (
            <p>{t('None')}</p>
          )}
        </section>
        <section>
          <h4>{t('Relationship reason')}</h4>
          <p dir="auto">
            {relationshipReason(relationship, questionReference, t)}
          </p>
        </section>
      </div>
      <dl className="material-reference-metadata">
        <div>
          <dt>{t('Reference type')}</dt>
          <dd>
            {t(
              relationship.result === 'nearby'
                ? 'Implicit nearby reference'
                : 'Explicit labelled reference',
            )}
          </dd>
        </div>
        <div>
          <dt>{t('Reference identity')}</dt>
          <dd dir="auto">
            {t(relationship.reference.target_type.replace('_', ' '))}:{' '}
            <bdi dir="auto">{relationship.reference.target_label}</bdi>
          </dd>
        </div>
      </dl>
      <p className="comparison-source-metadata">
        {t('Question page')}: {question?.page_number ?? relationship.reference.page_number}
        {' · '}
        {t('Reference source')}: {t('Exam')}
      </p>
    </details>
  )
}

export function StructuredEvidenceSection({ analysisId }: { analysisId: string }) {
  const { locale, t } = useI18n()
  const [data, setData] = useState<StructuredData | null>(null)
  const [error, setError] = useState<string | null>(null)

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
          setData({ materials, annotations, references, questions })
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(
            localizeInterfaceError(
              loadError,
              locale,
              t,
              'Could not load supporting-material evidence.',
            ),
          )
        }
      })
    return () => {
      cancelled = true
    }
  }, [analysisId, locale, t])

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
    return {
      materials,
      references,
      questionsById: new Map(
        data.questions.map((question) => [question.id, question]),
      ),
    }
  }, [data])

  if (error) {
    return (
      <PageState
        state="error"
        title={t('Could not load supporting-material evidence')}
        message={error}
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
  if (presentation.materials.length === 0 && presentation.references.length === 0) {
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
            {t(
              'Review how each question reference relates to the physical materials identified in the exam.',
            )}
          </p>
          <MethodologyLink anchor="evidence-traceability" />
        </div>
      </div>

      {presentation.references.length > 0 ? (
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
            {presentation.references.map((relationship) => {
              const question = relationship.reference.question_id
                ? presentation.questionsById.get(relationship.reference.question_id)
                : undefined
              const questionReference =
                question?.number_label ?? t('Unknown question')
              const matchedText =
                relationship.result === 'ambiguous'
                  ? t('{count} possible matches', {
                      count: relationship.exactCandidates.length,
                    })
                  : relationship.matchedMaterial
                    ? materialName(relationship.matchedMaterial, t)
                    : t('None')
              return (
                <tr key={relationship.reference.id}>
                  <th scope="row" data-label={t('Question')}>
                    <bdi>{questionReference}</bdi>
                  </th>
                  <td data-label={t('Referenced item')} dir="auto">
                    <bdi dir="auto">{relationship.reference.original_text}</bdi>
                  </td>
                  <td data-label={t('Matched material')} dir="auto">
                    {matchedText}
                  </td>
                  <td data-label={t('Relationship result')}>
                    <span
                      className="material-relationship-status"
                      data-relationship-result={relationship.result}
                    >
                      {t(RESULT_LABELS[relationship.result])}
                    </span>
                  </td>
                  <td data-label={t('Page')}>
                    <bdi>{candidatePages(relationship)}</bdi>
                  </td>
                  <td data-label={t('Details')}>
                    <RelationshipDetails
                      relationship={relationship}
                      question={question}
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </ResponsiveTable>
      ) : (
        <p className="results-empty-state">
          {t('No question-to-material references were identified.')}
        </p>
      )}

      {presentation.materials.length > 0 && (
        <details className="coverage-table-disclosure physical-material-inventory">
          <summary>
            <span>
              {t('Physical material inventory')} ({presentation.materials.length})
            </span>
            <small>
              {t(
                'One record per figure, table, diagram, or code block; labels and captions are attributes.',
              )}
            </small>
          </summary>
          <ResponsiveTable
            caption={t('Physical material inventory')}
            className="academic-summary-table"
          >
            <thead>
              <tr>
                <th scope="col">{t('Material')}</th>
                <th scope="col">{t('Type')}</th>
                <th scope="col">{t('Label')}</th>
                <th scope="col">{t('Caption or title')}</th>
                <th scope="col">{t('Page')}</th>
                <th scope="col">{t('Related questions')}</th>
                <th scope="col">{t('Status')}</th>
              </tr>
            </thead>
            <tbody>
              {presentation.materials.map((material) => {
                const relationships = presentation.references.filter(
                  (relationship) =>
                    relationship.exactCandidates.some(
                      (candidate) =>
                        candidate.material.id === material.material.id,
                    ) ||
                    relationship.nearbyCandidates.some(
                      (candidate) =>
                        candidate.material.id === material.material.id,
                    ),
                )
                const relatedQuestions = relationships.map((relationship) => {
                  const questionId = relationship.reference.question_id
                  return questionId
                    ? presentation.questionsById.get(questionId)?.number_label
                    : undefined
                })
                return (
                  <tr key={material.material.id}>
                    <th scope="row" data-label={t('Material')} dir="auto">
                      {materialName(material, t)}
                    </th>
                    <td data-label={t('Type')}>
                      {t(material.material.material_type.replace('_', ' '))}
                    </td>
                    <td data-label={t('Label')} dir="auto">
                      {material.label ?? t('Unlabelled')}
                    </td>
                    <td data-label={t('Caption or title')} dir="auto">
                      {material.caption ?? t('None')}
                    </td>
                    <td data-label={t('Page')}>
                      {material.material.page_number}
                    </td>
                    <td data-label={t('Related questions')}>
                      {relatedQuestions.length > 0
                        ? relatedQuestions.map((question, index) => (
                            <span key={`${material.material.id}-${question}`}>
                              {index > 0 && ', '}
                              <bdi>{question}</bdi>
                            </span>
                          ))
                        : t('None')}
                    </td>
                    <td data-label={t('Status')}>
                      {relationships.length > 0
                        ? [
                            ...new Set(
                              relationships.map((relationship) =>
                                t(RESULT_LABELS[relationship.result]),
                              ),
                            ),
                          ].join(', ')
                        : t('Not referenced')}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </ResponsiveTable>
        </details>
      )}
    </div>
  )
}
