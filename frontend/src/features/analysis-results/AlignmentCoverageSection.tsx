import { useRef, useState } from 'react'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { useI18n } from '../../i18n/I18nProvider'
import type {
  AcademicStatus,
  CloResponse,
  FindingEvidenceRef,
  FindingResponse,
  QuestionResponse,
  TopicResponse,
} from '../../types/api'
import { ALIGNMENT_COVERAGE_DIMENSIONS } from './dimensions'
import {
  independentlyScorableQuestions,
  sortQuestionReferences,
  sortQuestionsForFaculty,
} from './facultyOrdering'
import { MethodologyLink } from './MethodologyLink'
import { RelationshipMappingDrawer } from './RelationshipMappingDrawer'
import { QuestionRelationshipDrawer } from './QuestionRelationshipDrawer'
import { ResultResourceState } from './ResultResourceState'
import { StatusBadge } from './StatusBadge'
import type { ResultResource, ResultsResourceKey } from './useAnalysisResultsData'

interface AlignmentCoverageSectionProps {
  findings: ResultResource<FindingResponse[]>
  questions: ResultResource<QuestionResponse[]>
  clos: ResultResource<CloResponse[]>
  topics: ResultResource<TopicResponse[]>
  onRetry: (resource: ResultsResourceKey) => void
}

export type RelationshipKind = 'clo' | 'topic'

export interface RelationshipJudgment {
  key: string
  kind: RelationshipKind
  status: AcademicStatus
  reasoning: string
  targets: FindingEvidenceRef[]
}

export interface QuestionRelationshipRow {
  questionReference: string
  question: QuestionResponse | undefined
  sourceEvidence: FindingEvidenceRef | undefined
  cloJudgments: RelationshipJudgment[]
  topicJudgments: RelationshipJudgment[]
}

export type MappingTarget =
  | { kind: 'clo'; record: CloResponse }
  | { kind: 'topic'; record: TopicResponse }

interface SummaryArea {
  key: string
  title: string
  metrics: Array<{
    label: string
    value: number | string
  }>
}

export function facultyReason(
  status: AcademicStatus,
  sourceReason: string,
  locale: 'ar' | 'en',
  t: (key: string) => string,
): string {
  if (status === 'Partially Satisfied') {
    return t(
      'The question shares a relevant concept with the suggested item, but the relationship is limited.',
    )
  }
  const containsInternalWording =
    /normalized|controlled target|local evidence|controlled identifier|semantic|token/u.test(
      sourceReason.toLocaleLowerCase(),
    )
  if (locale === 'en' && sourceReason.trim() && !containsInternalWording) {
    return sourceReason
  }
  switch (status) {
    case 'Satisfied':
      return t(
        'The question and suggested item share relevant assessed content.',
      )
    case 'Not Satisfied':
      return t('No supported relationship found')
    case 'Not Verified':
      return t(
        'The available evidence was insufficient for a reliable relationship judgment.',
      )
    case 'Not Applicable':
      return t('This relationship does not apply to this analysis.')
  }
}

export function coverageStatus(judgments: RelationshipJudgment[]): AcademicStatus {
  if (judgments.some((judgment) => judgment.status === 'Satisfied')) {
    return 'Satisfied'
  }
  if (
    judgments.some((judgment) => judgment.status === 'Partially Satisfied')
  ) {
    return 'Partially Satisfied'
  }
  if (judgments.some((judgment) => judgment.status === 'Not Verified')) {
    return 'Not Verified'
  }
  if (judgments.some((judgment) => judgment.status === 'Not Applicable')) {
    return 'Not Applicable'
  }
  return 'Not Satisfied'
}

export function questionRows(
  cloFindings: FindingResponse[],
  topicFindings: FindingResponse[],
  questions: QuestionResponse[],
): QuestionRelationshipRow[] {
  const rows = new Map<string, QuestionRelationshipRow>()
  const questionByReference = new Map(
    questions.map((question) => [question.number_label, question]),
  )

  for (const question of questions) {
    rows.set(question.number_label, {
      questionReference: question.number_label,
      question,
      sourceEvidence: undefined,
      cloJudgments: [],
      topicJudgments: [],
    })
  }

  function addFindings(
    findings: FindingResponse[],
    kind: RelationshipKind,
  ): void {
    for (const finding of findings) {
      if (!finding.evaluation_details) continue
      const evidenceById = new Map(
        finding.evidence.map((evidence) => [evidence.id, evidence]),
      )
      finding.evaluation_details.item_judgments.forEach((judgment, index) => {
        const sourceEvidence = evidenceById.get(judgment.source_evidence_id)
        const questionReference =
          sourceEvidence?.item_reference ?? judgment.source_evidence_id
        if (!questionByReference.has(questionReference)) return
        const row = rows.get(questionReference) ?? {
          questionReference,
          question: questionByReference.get(questionReference),
          sourceEvidence,
          cloJudgments: [],
          topicJudgments: [],
        }
        row.sourceEvidence ??= sourceEvidence
        row[`${kind}Judgments`].push({
          key: `${finding.id}-${judgment.source_evidence_id}-${index}`,
          kind,
          status: judgment.status,
          reasoning: judgment.reasoning,
          targets: judgment.target_evidence_ids
            .map((id) => evidenceById.get(id))
            .filter((target): target is FindingEvidenceRef => target !== undefined),
        })
        rows.set(questionReference, row)
      })
    }
  }

  addFindings(cloFindings, 'clo')
  addFindings(topicFindings, 'topic')

  const pageByReference = new Map(
    [...rows.values()].map((row) => [
      row.questionReference,
      row.question?.page_number ?? row.sourceEvidence?.page_number ?? 0,
    ]),
  )
  const orderedReferences = sortQuestionReferences(
    [...rows.keys()],
    questions,
    pageByReference,
  )
  return orderedReferences.map((reference) => rows.get(reference)!)
}

export function uniqueTargets(judgments: RelationshipJudgment[]): FindingEvidenceRef[] {
  const targets = new Map<string, FindingEvidenceRef>()
  for (const judgment of judgments) {
    for (const target of judgment.targets) targets.set(target.id, target)
  }
  return [...targets.values()]
}

function recordMatchesTarget(
  record: CloResponse | TopicResponse,
  target: FindingEvidenceRef,
): boolean {
  if ('program_outcome_reference' in record) {
    return record.code === target.item_reference
  }
  return (
    record.code === target.item_reference || record.text === target.item_reference
  )
}

export function relatedRows(
  rows: QuestionRelationshipRow[],
  record: CloResponse | TopicResponse,
  kind: RelationshipKind,
): QuestionRelationshipRow[] {
  return rows.filter((row) =>
    row[`${kind}Judgments`].some((judgment) =>
      judgment.targets.some((target) => recordMatchesTarget(record, target)),
    ),
  )
}

export function matchingJudgments(
  row: QuestionRelationshipRow,
  record: CloResponse | TopicResponse,
  kind: RelationshipKind,
): RelationshipJudgment[] {
  return row[`${kind}Judgments`].filter((judgment) =>
    judgment.targets.some((target) => recordMatchesTarget(record, target)),
  )
}

export function totalMarksForRecord(
  rows: QuestionRelationshipRow[],
  record: CloResponse | TopicResponse,
  kind: RelationshipKind,
): number {
  return relatedRows(rows, record, kind)
    .filter((row) =>
      matchingJudgments(row, record, kind).some(
        (judgment) => judgment.status === 'Satisfied' || judgment.status === 'Partially Satisfied',
      ),
    )
    .reduce((total, row) => total + (row.question?.marks ?? 0), 0)
}

function linkedQuestionCount(
  rows: QuestionRelationshipRow[],
  kind: RelationshipKind,
): number {
  const judgmentsFor = (row: QuestionRelationshipRow) =>
    row[`${kind}Judgments`]
  return rows.filter((row) =>
    judgmentsFor(row).some(
      (judgment) =>
        judgment.targets.length > 0 &&
        (judgment.status === 'Satisfied' ||
          judgment.status === 'Partially Satisfied'),
    ),
  ).length
}

function coveredRecordCount(
  records: Array<CloResponse | TopicResponse>,
  rows: QuestionRelationshipRow[],
  kind: RelationshipKind,
): number {
  return records.filter((record) => {
    const status = coverageStatus(
      relatedRows(rows, record, kind).flatMap((row) =>
        matchingJudgments(row, record, kind),
      ),
    )
    return status === 'Satisfied' || status === 'Partially Satisfied'
  }).length
}

function ResourceIssue({
  resource,
  label,
  resourceKey,
  onRetry,
}: {
  resource: ResultResource<unknown>
  label: string
  resourceKey: ResultsResourceKey
  onRetry: (resource: ResultsResourceKey) => void
}) {
  const { t } = useI18n()
  if (resource.status === 'loading') {
    return (
      <p className="results-resource-state" role="status">
        {t('Loading {label}…', { label: t(label) })}
      </p>
    )
  }
  if (resource.status !== 'error') return null
  return (
    <Alert variant="error" title={t('Could not load {label}', { label: t(label) })}>
      <p>{resource.message}</p>
      <Button variant="secondary" onClick={() => onRetry(resourceKey)}>
        {t('Retry')}
      </Button>
    </Alert>
  )
}

function TargetReferences({
  judgments,
}: {
  judgments: RelationshipJudgment[]
}) {
  const { t } = useI18n()
  const targets = uniqueTargets(judgments)
  if (targets.length === 0) return <>{t('No supported relationship found')}</>
  return (
    <>
      {targets.map((target, index) => (
        <span key={target.id}>
          {index > 0 && ', '}
          <bdi>{target.item_reference}</bdi>
        </span>
      ))}
    </>
  )
}

function RelationshipStates({
  row,
}: {
  row: QuestionRelationshipRow
}) {
  const { t } = useI18n()
  const states: Array<[string, RelationshipJudgment[]]> = [
    ['CLO', row.cloJudgments],
    ['Course Topic', row.topicJudgments],
  ]
  const badge = (status: AcademicStatus, key: string) => (
    <StatusBadge key={key} status={status} />
  )
  return (
    <ul className="relationship-status-list">
      {states.map(([label, judgments]) => (
        <li key={label}>
          <strong>{t(label)}:</strong>{' '}
          <span className="relationship-badge-list">
            {judgments.length === 0
              ? badge('Not Satisfied', `${label}-unsupported`)
              : judgments.map((judgment) =>
                  badge(judgment.status, judgment.key),
                )}
          </span>
        </li>
      ))}
    </ul>
  )
}

function RelationshipReasons({
  row,
}: {
  row: QuestionRelationshipRow
}) {
  const { locale, t } = useI18n()
  const groups: Array<[string, RelationshipJudgment[]]> = [
    ['CLO', row.cloJudgments],
    ['Course Topic', row.topicJudgments],
  ]
  return (
    <ul className="relationship-reason-list">
      {groups.map(([label, judgments]) => (
        <li key={label}>
          <strong>{t(label)}:</strong>{' '}
          <span dir="auto">
            {judgments.length === 0
              ? t('No supported relationship found')
              : judgments
                  .map((judgment) =>
                    facultyReason(
                      judgment.status,
                      judgment.reasoning,
                      locale,
                      t,
                    ),
                  )
                  .join(' ')}
          </span>
        </li>
      ))}
    </ul>
  )
}


export function AlignmentCoverageSection({
  findings,
  questions,
  clos,
  topics,
  onRetry,
}: AlignmentCoverageSectionProps) {
  const { t } = useI18n()
  const [selectedRow, setSelectedRow] = useState<QuestionRelationshipRow | null>(null)
  const [mappingTarget, setMappingTarget] = useState<MappingTarget | null>(null)
  const mappingTriggerRefs = useRef(new Map<string, HTMLButtonElement>())
  const activeMappingTriggerRef = useRef<HTMLButtonElement | null>(null)
  const loadedQuestions =
    questions.status === 'ready'
      ? sortQuestionsForFaculty(independentlyScorableQuestions(questions.data))
      : []
  const loadedClos = clos.status === 'ready' ? clos.data : []
  const loadedTopics = topics.status === 'ready' ? topics.data : []

  function openComparison(row: QuestionRelationshipRow, triggerKey: string): void {
    activeMappingTriggerRef.current = mappingTriggerRefs.current.get(triggerKey) ?? null
    setSelectedRow(row)
  }

  function openMapping(target: MappingTarget, triggerKey: string): void {
    activeMappingTriggerRef.current = mappingTriggerRefs.current.get(triggerKey) ?? null
    setMappingTarget(target)
  }

  return (
    <div className="alignment-coverage-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Alignment & Coverage')}</h2>
          <p>
            {t(
              'Review suggested question relationships and the resulting coverage of Course Specification outcomes and topics.',
            )}
          </p>
          <MethodologyLink anchor="suggested-relationships" />
        </div>
      </div>

      <ResultResourceState
        resource={findings}
        loadingMessage={t('Loading alignment and coverage findings…')}
        errorTitle={t('Could not load alignment and coverage findings')}
        onRetry={() => onRetry('findings')}
      >
        {(loadedFindings) => {
          const relevant = loadedFindings.filter(
            (finding) => ALIGNMENT_COVERAGE_DIMENSIONS.has(finding.dimension),
          )
          const cloRelationshipFindings = relevant.filter(
            (finding) => finding.rule_id === 'RULE001',
          )
          const topicRelationshipFindings = relevant.filter(
            (finding) => finding.rule_id === 'RULE007',
          )
          const rows = questionRows(
            cloRelationshipFindings,
            topicRelationshipFindings,
            loadedQuestions,
          )
          const summaryAreas: SummaryArea[] = [
            {
              key: 'question-relationships',
              title: 'Question Relationships',
              metrics: [
                {
                  label: 'Questions linked to a CLO',
                  value: linkedQuestionCount(rows, 'clo'),
                },
                {
                  label: 'Questions linked to a course topic',
                  value: linkedQuestionCount(rows, 'topic'),
                },
              ],
            },
            {
              key: 'coverage',
              title: 'Coverage',
              metrics: [
                {
                  label: 'CLO Coverage',
                  value: `${coveredRecordCount(loadedClos, rows, 'clo')}/${loadedClos.length}`,
                },
                {
                  label: 'Topic Coverage',
                  value: `${coveredRecordCount(loadedTopics, rows, 'topic')}/${loadedTopics.length}`,
                },
              ],
            },
          ]

          if (relevant.length === 0) {
            return (
              <p className="results-empty-state">
                {t('No alignment or coverage findings are available.')}
              </p>
            )
          }

          return (
            <>
              <section aria-labelledby="alignment-summary-heading">
                <h3 id="alignment-summary-heading">
                  {t('Alignment and coverage summary')}
                </h3>
                <ul
                  className="alignment-compact-summary"
                  aria-label={t('Alignment and coverage summary')}
                >
                  {summaryAreas.map((area) => (
                    <li key={area.key}>
                      <h4>{t(area.title)}</h4>
                      <dl>
                        {area.metrics.map((metric) => (
                          <div key={metric.label}>
                            <dt>{t(metric.label)}</dt>
                            <dd>{metric.value}</dd>
                          </div>
                        ))}
                      </dl>
                    </li>
                  ))}
                </ul>
              </section>

              <p className="alignment-advisory-notice">
                {t(
                  'The displayed relationships are analytical suggestions for review. They are not official mappings from the Course Specification and do not modify the original documents.',
                )}
              </p>

              <section
                className="academic-table-section"
                id="question-relationships"
              >
                <h3>{t('Question-to-CLO-and-Topic relationships')}</h3>
                <ResponsiveTable
                  caption={t('Question-to-CLO-and-Topic relationships')}
                  className="combined-relationship-table"
                >
                  <thead>
                    <tr>
                      <th scope="col">{t('Question')}</th>
                      <th scope="col">{t('Suggested CLO')}</th>
                      <th scope="col">{t('Suggested Course Topic')}</th>
                      <th scope="col">{t('Alignment status')}</th>
                      <th scope="col">{t('Short reason')}</th>
                      <th scope="col">{t('Details')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr key={row.questionReference}>
                        <th scope="row" data-label={t('Question')}>
                          <bdi>{row.questionReference}</bdi>
                        </th>
                        <td data-label={t('Suggested CLO')}>
                          <TargetReferences judgments={row.cloJudgments} />
                        </td>
                        <td data-label={t('Suggested Course Topic')}>
                          <TargetReferences judgments={row.topicJudgments} />
                        </td>
                        <td data-label={t('Alignment status')}>
                          <RelationshipStates row={row} />
                        </td>
                        <td data-label={t('Short reason')}>
                          <RelationshipReasons row={row} />
                        </td>
                        <td data-label={t('Details')}>
                          <button
                            ref={(element) => {
                              const triggerKey = `question-${row.questionReference}`
                              if (element) mappingTriggerRefs.current.set(triggerKey, element)
                              else mappingTriggerRefs.current.delete(triggerKey)
                            }}
                            type="button"
                            className="inline-evidence-action"
                            onClick={() =>
                              openComparison(row, `question-${row.questionReference}`)
                            }
                          >
                            {t('View mapping details')}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </ResponsiveTable>
              </section>



              <section className="academic-table-section" id="clo-coverage">
                <h3>
                  {t('CLO Analysis')} ({loadedClos.length})
                </h3>
                <ResponsiveTable
                  caption={t('CLO Analysis')}
                  className="academic-summary-table"
                >
                  <thead>
                    <tr>
                      <th scope="col">{t('CLO')}</th>
                      <th scope="col">{t('CLO text')}</th>
                      <th scope="col">{t('Linked questions')}</th>
                      <th scope="col">{t('Coverage status')}</th>
                      <th scope="col">{t('Total marks')}</th>
                      <th scope="col">{t('Details')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadedClos.map((clo) => {
                      const matches = relatedRows(rows, clo, 'clo')
                      const judgments = matches.flatMap((row) =>
                        matchingJudgments(row, clo, 'clo'),
                      )
                      const orderedReferences = sortQuestionReferences(
                        matches.map((row) => row.questionReference),
                        loadedQuestions,
                      )
                      const triggerKey = `clo-${clo.id}`
                      return (
                        <tr key={clo.id}>
                          <th scope="row" data-label={t('CLO')}>
                            <bdi>{clo.code}</bdi>
                          </th>
                          <td data-label={t('CLO text')}>
                            <span dir="auto">{clo.text}</span>
                          </td>
                          <td data-label={t('Linked questions')}>
                            {orderedReferences.length === 0
                              ? t('None')
                              : orderedReferences.map((reference, index) => (
                                  <span key={reference}>
                                    {index > 0 && ', '}
                                    <bdi>{reference}</bdi>
                                  </span>
                                ))}
                          </td>
                          <td data-label={t('Coverage status')}>
                            <StatusBadge status={coverageStatus(judgments)} />
                          </td>
                          <td data-label={t('Total marks')}>
                            {totalMarksForRecord(rows, clo, 'clo')}
                          </td>
                          <td data-label={t('Details')}>
                            <button
                              ref={(element) => {
                                if (element) mappingTriggerRefs.current.set(triggerKey, element)
                                else mappingTriggerRefs.current.delete(triggerKey)
                              }}
                              type="button"
                              className="inline-evidence-action"
                              onClick={() =>
                                openMapping({ kind: 'clo', record: clo }, triggerKey)
                              }
                            >
                              {t('View mapping details')}
                            </button>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </ResponsiveTable>
              </section>

              <section className="academic-table-section" id="topic-coverage">
                <h3>
                  {t('Topic Analysis')} ({loadedTopics.length})
                </h3>
                <p className="results-supporting-text">
                  {t(
                    'A Midterm or Final exam may legitimately cover a subset of course topics. Topic coverage is informational and does not by itself indicate a quality problem.',
                  )}
                </p>
                <ResponsiveTable
                  caption={t('Topic Analysis')}
                  className="academic-summary-table"
                >
                  <thead>
                    <tr>
                      <th scope="col">{t('Course Topic')}</th>
                      <th scope="col">{t('Linked questions')}</th>
                      <th scope="col">{t('Total marks')}</th>
                      <th scope="col">{t('Coverage status')}</th>
                      <th scope="col">{t('Details')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loadedTopics.map((topic) => {
                      const matches = relatedRows(rows, topic, 'topic')
                      const judgments = matches.flatMap((row) =>
                        matchingJudgments(row, topic, 'topic'),
                      )
                      const orderedReferences = sortQuestionReferences(
                        matches.map((row) => row.questionReference),
                        loadedQuestions,
                      )
                      const triggerKey = `topic-${topic.id}`
                      return (
                        <tr key={topic.id}>
                          <th scope="row" data-label={t('Course Topic')}>
                            <span dir="auto">{topic.text}</span>
                          </th>
                          <td data-label={t('Linked questions')}>
                            {orderedReferences.length === 0
                              ? t('None')
                              : orderedReferences.map((reference, index) => (
                                  <span key={reference}>
                                    {index > 0 && ', '}
                                    <bdi>{reference}</bdi>
                                  </span>
                                ))}
                          </td>
                          <td data-label={t('Total marks')}>
                            {totalMarksForRecord(rows, topic, 'topic')}
                          </td>
                          <td data-label={t('Coverage status')}>
                            <StatusBadge status={coverageStatus(judgments)} />
                          </td>
                          <td data-label={t('Details')}>
                            {matches.length === 0 ? (
                              '—'
                            ) : (
                              <button
                                ref={(element) => {
                                  if (element)
                                    mappingTriggerRefs.current.set(triggerKey, element)
                                  else mappingTriggerRefs.current.delete(triggerKey)
                                }}
                                type="button"
                                className="inline-evidence-action"
                                onClick={() =>
                                  openMapping({ kind: 'topic', record: topic }, triggerKey)
                                }
                              >
                                {t('View mapping details')}
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </ResponsiveTable>
              </section>

              <QuestionRelationshipDrawer
                row={selectedRow}
                clos={loadedClos}
                topics={loadedTopics}
                onClose={() => setSelectedRow(null)}
                returnFocusRef={activeMappingTriggerRef}
              />

              <RelationshipMappingDrawer
                target={mappingTarget}
                rows={rows}
                onClose={() => setMappingTarget(null)}
                returnFocusRef={activeMappingTriggerRef}
              />
            </>
          )
        }}
      </ResultResourceState>

      <ResourceIssue
        resource={questions}
        label="Questions"
        resourceKey="questions"
        onRetry={onRetry}
      />
      <ResourceIssue
        resource={clos}
        label="Course Specification CLOs"
        resourceKey="clos"
        onRetry={onRetry}
      />
      <ResourceIssue
        resource={topics}
        label="Course Specification topics"
        resourceKey="topics"
        onRetry={onRetry}
      />
    </div>
  )
}
