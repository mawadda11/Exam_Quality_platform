import { useRef, useState } from 'react'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ResponsiveTable } from '../../components/ui/ResponsiveTable'
import { presentFindingExplanation } from '../../i18n/governedPresentation'
import { useI18n } from '../../i18n/I18nProvider'
import type {
  AcademicStatus,
  AnalysisResponse,
  AssessmentRecordResponse,
  CloResponse,
  FindingEvidenceRef,
  FindingResponse,
  QuestionResponse,
  TopicResponse,
} from '../../types/api'
import { ALIGNMENT_COVERAGE_DIMENSIONS } from './dimensions'
import {
  sortQuestionReferences,
  sortQuestionsForFaculty,
} from './facultyOrdering'
import { MethodologyLink } from './MethodologyLink'
import { ResultResourceState } from './ResultResourceState'
import { StatusBadge } from './StatusBadge'
import type { ResultResource, ResultsResourceKey } from './useAnalysisResultsData'

interface AlignmentCoverageSectionProps {
  analysis: AnalysisResponse
  findings: ResultResource<FindingResponse[]>
  questions: ResultResource<QuestionResponse[]>
  clos: ResultResource<CloResponse[]>
  topics: ResultResource<TopicResponse[]>
  assessmentRecords: ResultResource<AssessmentRecordResponse[]>
  onRetry: (resource: ResultsResourceKey) => void
}

type RelationshipKind = 'clo' | 'topic'

interface RelationshipJudgment {
  key: string
  kind: RelationshipKind
  status: AcademicStatus
  reasoning: string
  targets: FindingEvidenceRef[]
}

interface QuestionRelationshipRow {
  questionReference: string
  question: QuestionResponse | undefined
  sourceEvidence: FindingEvidenceRef | undefined
  cloJudgments: RelationshipJudgment[]
  topicJudgments: RelationshipJudgment[]
}

interface SummaryArea {
  key: string
  title: string
  status: AcademicStatus | undefined
  count: number
  countMessage: string
}

function facultyReason(
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

function supportedState(status: AcademicStatus): string {
  switch (status) {
    case 'Satisfied':
      return 'Supported'
    case 'Partially Satisfied':
      return 'Partially supported'
    case 'Not Satisfied':
      return 'No supported relationship found'
    case 'Not Verified':
      return 'Could not be verified'
    case 'Not Applicable':
      return 'Not Applicable'
  }
}

function coverageStatus(judgments: RelationshipJudgment[]): AcademicStatus {
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

function questionRows(
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

function uniqueTargets(judgments: RelationshipJudgment[]): FindingEvidenceRef[] {
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

function relatedRows(
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

function matchingJudgments(
  row: QuestionRelationshipRow,
  record: CloResponse | TopicResponse,
  kind: RelationshipKind,
): RelationshipJudgment[] {
  return row[`${kind}Judgments`].filter((judgment) =>
    judgment.targets.some((target) => recordMatchesTarget(record, target)),
  )
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
  return (
    <ul className="relationship-status-list">
      {states.map(([label, judgments]) => (
        <li key={label}>
          <strong>{t(label)}:</strong>{' '}
          {judgments.length === 0
            ? t('No supported relationship found')
            : judgments.map((judgment, index) => (
                <span key={judgment.key}>
                  {index > 0 && ', '}
                  {t(supportedState(judgment.status))}
                </span>
              ))}
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

function CompactMetadata({
  reference,
  source,
  page,
}: {
  reference: string
  source: string
  page: number | undefined
}) {
  const { t } = useI18n()
  return (
    <small className="comparison-source-metadata">
      <bdi>{reference}</bdi> — {t(source)}
      {page ? `, ${t('page')} ${page}` : ''}
    </small>
  )
}

function QuestionComparison({
  row,
  clos,
  topics,
  onClose,
}: {
  row: QuestionRelationshipRow
  clos: CloResponse[]
  topics: TopicResponse[]
  onClose: () => void
}) {
  const { locale, t } = useI18n()
  const cloTargets = uniqueTargets(row.cloJudgments)
  const topicTargets = uniqueTargets(row.topicJudgments)
  return (
    <>
      <summary
        onClick={(event) => {
          event.preventDefault()
          onClose()
        }}
      >
        {t('View comparison')} — <bdi>{row.questionReference}</bdi>
      </summary>
      <div className="comparison-grid">
        <section>
          <h4>{t('Question text')}</h4>
          <p dir="auto">
            {row.question?.question_text ?? t('Question text is unavailable.')}
          </p>
          <CompactMetadata
            reference={row.questionReference}
            source="Exam"
            page={row.question?.page_number ?? row.sourceEvidence?.page_number}
          />
        </section>

        {cloTargets.map((target) => {
          const clo = clos.find((item) => item.code === target.item_reference)
          const judgments = row.cloJudgments.filter((judgment) =>
            judgment.targets.some((item) => item.id === target.id),
          )
          return (
            <section key={target.id}>
              <h4>{t('Suggested CLO')}</h4>
              <p dir="auto">{clo?.text ?? target.item_reference}</p>
              <p className="comparison-reason" dir="auto">
                <strong>{t('Relationship reason')}:</strong>{' '}
                {judgments
                  .map((judgment) =>
                    facultyReason(
                      judgment.status,
                      judgment.reasoning,
                      locale,
                      t,
                    ),
                  )
                  .join(' ')}
              </p>
              <CompactMetadata
                reference={clo?.code ?? target.item_reference}
                source="Course Specification"
                page={clo?.page_number ?? target.page_number}
              />
            </section>
          )
        })}

        {topicTargets.map((target) => {
          const topic = topics.find(
            (item) =>
              item.code === target.item_reference ||
              item.text === target.item_reference,
          )
          const judgments = row.topicJudgments.filter((judgment) =>
            judgment.targets.some((item) => item.id === target.id),
          )
          return (
            <section key={target.id}>
              <h4>{t('Suggested Course Topic')}</h4>
              <p dir="auto">{topic?.text ?? target.item_reference}</p>
              <p className="comparison-reason" dir="auto">
                <strong>{t('Relationship reason')}:</strong>{' '}
                {judgments
                  .map((judgment) =>
                    facultyReason(
                      judgment.status,
                      judgment.reasoning,
                      locale,
                      t,
                    ),
                  )
                  .join(' ')}
              </p>
              <CompactMetadata
                reference={topic?.code ?? t('Course Topic')}
                source="Course Specification"
                page={topic?.page_number ?? target.page_number}
              />
            </section>
          )
        })}
      </div>
    </>
  )
}

function assessmentMatchesExamType(
  record: AssessmentRecordResponse,
  examType: AnalysisResponse['exam_type'],
): boolean {
  const value = `${record.method} ${record.activity ?? ''}`.toLocaleLowerCase()
  if (examType === 'Final') return /final|نهائي/u.test(value)
  return /mid[\s-]?term|نصفي|منتصف/u.test(value)
}

function AssessmentConsistency({
  analysis,
  findings,
  records,
}: {
  analysis: AnalysisResponse
  findings: FindingResponse[]
  records: AssessmentRecordResponse[]
}) {
  const { locale, t } = useI18n()
  const finding = findings[0]
  const match = records.find((record) =>
    assessmentMatchesExamType(record, analysis.exam_type),
  )
  return (
    <Card
      as="section"
      className="results-content-card assessment-consistency-section"
      id="assessment-method-consistency"
    >
      <div className="compact-assessment-heading">
        <h3>{t('Assessment Method Consistency')}</h3>
        {finding && <StatusBadge status={finding.status} />}
      </div>
      {finding ? (
        <p dir="auto">
          {finding.status === 'Satisfied' && match
            ? t(
                'The document was identified as a {examType}, and a matching assessment method was found in the Course Specification.',
                { examType: t(`${analysis.exam_type} Examination`) },
              )
            : presentFindingExplanation(finding, locale)}
        </p>
      ) : (
        <p>{t('No assessment-consistency result is available.')}</p>
      )}
      {finding && match && (
        <details className="assessment-comparison">
          <summary>{t('View comparison')}</summary>
          <dl>
            <div>
              <dt>{t('Detected Exam type')}</dt>
              <dd dir="auto">
                {t(`${analysis.exam_type} Examination`)}
                <CompactMetadata
                  reference={analysis.exam_type}
                  source="Exam"
                  page={undefined}
                />
              </dd>
            </div>
            <div>
              <dt>{t('Matching assessment method')}</dt>
              <dd dir="auto">
                {match.method}
                {match.activity ? ` — ${match.activity}` : ''}
                <CompactMetadata
                  reference={t('Assessment method')}
                  source="Course Specification"
                  page={match.page_number}
                />
              </dd>
            </div>
          </dl>
        </details>
      )}
    </Card>
  )
}

export function AlignmentCoverageSection({
  analysis,
  findings,
  questions,
  clos,
  topics,
  assessmentRecords,
  onRetry,
}: AlignmentCoverageSectionProps) {
  const { t } = useI18n()
  const [selectedRow, setSelectedRow] =
    useState<QuestionRelationshipRow | null>(null)
  const comparisonRef = useRef<HTMLDetailsElement>(null)
  const loadedQuestions =
    questions.status === 'ready' ? sortQuestionsForFaculty(questions.data) : []
  const loadedClos = clos.status === 'ready' ? clos.data : []
  const loadedTopics = topics.status === 'ready' ? topics.data : []
  const loadedAssessmentRecords =
    assessmentRecords.status === 'ready' ? assessmentRecords.data : []

  function openComparison(row: QuestionRelationshipRow): void {
    setSelectedRow(row)
    window.setTimeout(() => comparisonRef.current?.focus(), 0)
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
            (finding) =>
              ALIGNMENT_COVERAGE_DIMENSIONS.has(finding.dimension) ||
              finding.dimension === 'Assessment Alignment' ||
              finding.rule_id === 'RULE003',
          )
          const cloRelationshipFindings = relevant.filter(
            (finding) => finding.rule_id === 'RULE001',
          )
          const topicRelationshipFindings = relevant.filter(
            (finding) => finding.rule_id === 'RULE007',
          )
          const cloCoverageFindings = relevant.filter(
            (finding) => finding.dimension === 'CLO Coverage',
          )
          const topicCoverageFindings = relevant.filter(
            (finding) => finding.dimension === 'Topic Coverage',
          )
          const assessmentFindings = relevant.filter(
            (finding) =>
              finding.dimension === 'Assessment Alignment' ||
              finding.rule_id === 'RULE003',
          )
          const rows = questionRows(
            cloRelationshipFindings,
            topicRelationshipFindings,
            loadedQuestions,
          )
          const matchingAssessmentCount = loadedAssessmentRecords.filter(
            (record) => assessmentMatchesExamType(record, analysis.exam_type),
          ).length
          const summaryAreas: SummaryArea[] = [
            {
              key: 'clo-relationships',
              title: 'CLO Alignment',
              status: cloRelationshipFindings[0]?.status,
              count: rows.filter((row) => row.cloJudgments.length > 0).length,
              countMessage: '{count} suggested question relationships',
            },
            {
              key: 'topic-relationships',
              title: 'Topic Alignment',
              status: topicRelationshipFindings[0]?.status,
              count: rows.filter((row) => row.topicJudgments.length > 0).length,
              countMessage: '{count} suggested question relationships',
            },
            {
              key: 'clo-coverage',
              title: 'CLO Coverage',
              status: cloCoverageFindings[0]?.status,
              count: loadedClos.length,
              countMessage: '{count} Course Specification CLOs',
            },
            {
              key: 'topic-coverage',
              title: 'Topic Coverage',
              status: topicCoverageFindings[0]?.status,
              count: loadedTopics.length,
              countMessage: '{count} Course Specification topics',
            },
            {
              key: 'assessment',
              title: 'Assessment Method Consistency',
              status: assessmentFindings[0]?.status,
              count: matchingAssessmentCount,
              countMessage: '{count} matching assessment methods',
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
                      <span>{t(area.title)}</span>
                      <strong>
                        {t(area.countMessage, { count: area.count })}
                      </strong>
                      {area.status && <StatusBadge status={area.status} />}
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
                  className="academic-summary-table combined-relationship-table"
                >
                  <thead>
                    <tr>
                      <th scope="col">{t('Question')}</th>
                      <th scope="col">{t('Suggested CLO')}</th>
                      <th scope="col">{t('Suggested Course Topic')}</th>
                      <th scope="col">{t('Alignment status')}</th>
                      <th scope="col">{t('Short reason')}</th>
                      <th scope="col">{t('View comparison')}</th>
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
                        <td data-label={t('View comparison')}>
                          <button
                            type="button"
                            className="inline-evidence-action"
                            onClick={() => openComparison(row)}
                          >
                            {t('View comparison')}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </ResponsiveTable>
              </section>

              {selectedRow && (
                <details
                  ref={comparisonRef}
                  id="question-comparison"
                  className="question-comparison"
                  open
                  tabIndex={-1}
                >
                  <QuestionComparison
                    row={selectedRow}
                    clos={loadedClos}
                    topics={loadedTopics}
                    onClose={() => setSelectedRow(null)}
                  />
                </details>
              )}

              <section className="academic-table-section" id="clo-coverage">
                <h3>{t('CLO Coverage')}</h3>
                <ResponsiveTable
                  caption={t('CLO Coverage')}
                  className="academic-summary-table"
                >
                  <thead>
                    <tr>
                      <th scope="col">{t('CLO')}</th>
                      <th scope="col">{t('CLO text')}</th>
                      <th scope="col">{t('Coverage status')}</th>
                      <th scope="col">{t('Related questions')}</th>
                      <th scope="col">{t('Action')}</th>
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
                      return (
                        <tr key={clo.id}>
                          <th scope="row" data-label={t('CLO')}>
                            <bdi>{clo.code}</bdi>
                          </th>
                          <td data-label={t('CLO text')}>
                            <span dir="auto">{clo.text}</span>
                          </td>
                          <td data-label={t('Coverage status')}>
                            {t(supportedState(coverageStatus(judgments)))}
                          </td>
                          <td data-label={t('Related questions')}>
                            {orderedReferences.length === 0
                              ? t('None')
                              : orderedReferences.map((reference, index) => (
                                  <span key={reference}>
                                    {index > 0 && ', '}
                                    <bdi>{reference}</bdi>
                                  </span>
                                ))}
                          </td>
                          <td data-label={t('Action')}>
                            {matches[0] ? (
                              <button
                                type="button"
                                className="inline-evidence-action"
                                onClick={() => openComparison(matches[0])}
                              >
                                {t('View comparison')}
                              </button>
                            ) : (
                              '—'
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </ResponsiveTable>
              </section>

              <section className="academic-table-section" id="topic-coverage">
                <h3>{t('Topic Coverage')}</h3>
                <ResponsiveTable
                  caption={t('Topic Coverage')}
                  className="academic-summary-table"
                >
                  <thead>
                    <tr>
                      <th scope="col">{t('Course Topic')}</th>
                      <th scope="col">{t('Coverage status')}</th>
                      <th scope="col">{t('Related questions')}</th>
                      <th scope="col">{t('Action')}</th>
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
                      return (
                        <tr key={topic.id}>
                          <th scope="row" data-label={t('Course Topic')}>
                            <span dir="auto">{topic.text}</span>
                          </th>
                          <td data-label={t('Coverage status')}>
                            {t(supportedState(coverageStatus(judgments)))}
                          </td>
                          <td data-label={t('Related questions')}>
                            {orderedReferences.length === 0
                              ? t('None')
                              : orderedReferences.map((reference, index) => (
                                  <span key={reference}>
                                    {index > 0 && ', '}
                                    <bdi>{reference}</bdi>
                                  </span>
                                ))}
                          </td>
                          <td data-label={t('Action')}>
                            {matches[0] ? (
                              <button
                                type="button"
                                className="inline-evidence-action"
                                onClick={() => openComparison(matches[0])}
                              >
                                {t('View comparison')}
                              </button>
                            ) : (
                              '—'
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </ResponsiveTable>
              </section>

              <AssessmentConsistency
                analysis={analysis}
                findings={assessmentFindings}
                records={loadedAssessmentRecords}
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
      <ResourceIssue
        resource={assessmentRecords}
        label="Course Specification assessment methods"
        resourceKey="assessmentRecords"
        onRetry={onRetry}
      />
    </div>
  )
}
