import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getAnalysis,
  listDocumentReferences,
  listSupportingMaterialAnnotations,
  listSupportingMaterials,
} from '../../api/analyses'
import { PageState } from '../../components/ui/PageState'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import {
  presentFindingExplanation,
  presentRequirementName,
} from '../../i18n/governedPresentation'
import type {
  AnalysisResponse,
  DocumentReferenceResponse,
  ReportResponse,
  SupportingMaterialAnnotationResponse,
  SupportingMaterialResponse,
} from '../../types/api'
import {
  coverageStatus,
  matchingJudgments,
  questionRows,
  relatedRows,
  totalMarksForRecord,
} from '../analysis-results/AlignmentCoverageSection'
import { sortQuestionReferences } from '../analysis-results/facultyOrdering'
import { scoreImpactMessage } from '../analysis-results/findingPresentation'
import {
  buildMaterialRelationship,
  buildPhysicalMaterials,
} from '../analysis-results/materialRelationships'
import { StatusBadge } from '../analysis-results/StatusBadge'
import { RESULT_LABELS } from '../analysis-results/StructuredEvidenceSection'
import { useAnalysisResultsData } from '../analysis-results/useAnalysisResultsData'
import {
  buildExamSummary,
  groupFindingsForReport,
  groupRecommendationsForReport,
  statusDistributionCounts,
  STATUS_DISTRIBUTION_ORDER,
  strongestDimensions,
  weakestDimensions,
} from './reportPresentation'

interface ReportPreviewContentProps {
  analysisId: string
  report: ReportResponse
}

interface StructuredData {
  materials: SupportingMaterialResponse[]
  annotations: SupportingMaterialAnnotationResponse[]
  references: DocumentReferenceResponse[]
}

function useStructuredEvidence(analysisId: string) {
  const { locale, t } = useI18n()
  const [data, setData] = useState<StructuredData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      listSupportingMaterials(analysisId),
      listSupportingMaterialAnnotations(analysisId),
      listDocumentReferences(analysisId),
    ])
      .then(([materials, annotations, references]) => {
        if (!cancelled) setData({ materials, annotations, references })
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

  return { data, error }
}

function useAnalysisMetadata(analysisId: string) {
  const { locale, t } = useI18n()
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getAnalysis(analysisId)
      .then((data) => {
        if (!cancelled) setAnalysis(data)
      })
      .catch((loadError: unknown) => {
        if (!cancelled) {
          setError(localizeInterfaceError(loadError, locale, t, 'Could not load the analysis.'))
        }
      })
    return () => {
      cancelled = true
    }
  }, [analysisId, locale, t])

  return { analysis, error }
}

export function ReportPreviewContent({ analysisId, report }: ReportPreviewContentProps) {
  const { locale, t, formatDateTime } = useI18n()
  const { resources } = useAnalysisResultsData(analysisId)
  const structured = useStructuredEvidence(analysisId)
  const analysisMetadata = useAnalysisMetadata(analysisId)

  const loading =
    resources.questions.status === 'loading' ||
    resources.findings.status === 'loading' ||
    resources.clos.status === 'loading' ||
    resources.topics.status === 'loading' ||
    resources.score.status === 'loading' ||
    !structured.data ||
    (!analysisMetadata.analysis && !analysisMetadata.error)

  if (loading) {
    return (
      <PageState
        state="loading"
        title={t('Loading report preview')}
        message={t('Retrieving the governed analysis results…')}
      />
    )
  }

  if (
    resources.questions.status !== 'ready' ||
    resources.findings.status !== 'ready' ||
    resources.clos.status !== 'ready' ||
    resources.topics.status !== 'ready' ||
    resources.score.status !== 'ready' ||
    !structured.data ||
    !analysisMetadata.analysis
  ) {
    return (
      <PageState
        state="error"
        title={t('Report preview could not be loaded')}
        message={
          structured.error ??
          analysisMetadata.error ??
          t('One or more governed results could not be loaded for this report.')
        }
      />
    )
  }

  const analysis = analysisMetadata.analysis

  const questions = resources.questions.data
  const findings = resources.findings.data
  const clos = resources.clos.data
  const topics = resources.topics.data
  const score = resources.score.data
  const { materials, annotations, references } = structured.data

  const physicalMaterials = buildPhysicalMaterials(materials, annotations)
  const materialReferences = references
    .filter((reference) => reference.target_type !== 'question')
    .map((reference) => buildMaterialRelationship(reference, physicalMaterials))

  const examSummary = buildExamSummary(questions, findings, materials.length, materialReferences)
  const grouped = groupFindingsForReport(findings)
  const recommendationGroups = groupRecommendationsForReport(findings)
  const distribution = statusDistributionCounts(score)

  const cloFindings = findings.filter((finding) => finding.rule_id === 'RULE001')
  const topicFindings = findings.filter((finding) => finding.rule_id === 'RULE007')
  const rows = questionRows(cloFindings, topicFindings, questions)

  return (
    <div className="report-preview-sheet">
      <section aria-labelledby="report-section-1" className="report-preview-section">
        <h2 id="report-section-1">1. {t('Report Header')}</h2>
        <p className="report-preview-title">
          <bdi>{analysis.course.code}</bdi> — <span dir="auto">{analysis.course.name}</span>
        </p>
        <dl className="report-header-facts">
          <div>
            <dt>{t('Exam type')}</dt>
            <dd>{t(analysis.exam_type)}</dd>
          </div>
          <div>
            <dt>{t('Term')}</dt>
            <dd dir="auto">{analysis.term}</dd>
          </div>
          <div>
            <dt>{t('Generated')}</dt>
            <dd>
              <time dateTime={report.created_at}>{formatDateTime(report.created_at)}</time>
            </dd>
          </div>
          <div>
            <dt>{t('Report identifier')}</dt>
            <dd>
              <bdi>{report.id}</bdi>
            </dd>
          </div>
          <div>
            <dt>{t('Report language')}</dt>
            <dd>{t(report.language === 'ar' ? 'Arabic Report' : 'English Report')}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="report-section-2" className="report-preview-section">
        <h2 id="report-section-2">2. {t('Executive Summary')}</h2>
        <p>
          {t(
            'This report analyzes the uploaded exam against the Course Specification, covering question clarity, CLO and topic alignment and coverage, marks and structure, and supporting materials.',
          )}
        </p>
        <p>
          {score.score !== null
            ? t('Overall result: {score}% based on {count} verified applicable checks.', {
                score: score.score,
                count: score.denominator,
              })
            : t('Overall result: {label}.', { label: t(score.label ?? 'Insufficient Evidence') })}
        </p>
        {grouped.strengths.length > 0 && (
          <p>
            {t('Strongest verified areas: {areas}.', {
              areas: strongestDimensions(grouped.strengths)
                .map((dimension) => t(dimension))
                .join(', '),
            })}
          </p>
        )}
        {grouped.areasForImprovement.length > 0 && (
          <p>
            {t('Main areas requiring improvement: {areas}.', {
              areas: weakestDimensions(grouped.areasForImprovement)
                .map((dimension) => t(dimension))
                .join(', '),
            })}
          </p>
        )}
        {grouped.missingEvidence.length > 0 && (
          <p>
            {t('{count} result(s) could not be verified due to missing or unreliable evidence.', {
              count: grouped.missingEvidence.length,
            })}
          </p>
        )}
      </section>

      <section aria-labelledby="report-section-3" className="report-preview-section">
        <h2 id="report-section-3">3. {t('Overall Exam Quality Score')}</h2>
        <ScoreRing score={score.score} denominator={score.denominator} emptyLabel={t(score.label ?? 'Insufficient Evidence')} />
      </section>

      <section aria-labelledby="report-section-4" className="report-preview-section">
        <h2 id="report-section-4">4. {t('Status Distribution')}</h2>
        <ul className="report-status-distribution">
          {STATUS_DISTRIBUTION_ORDER.map((status) => (
            <li key={status}>
              <strong>{distribution[status]}</strong>
              <StatusBadge status={status} />
            </li>
          ))}
        </ul>
        <p className="results-supporting-text">
          {t(
            'Not Verified and Not Applicable results remain visible but are excluded from the score denominator.',
          )}
        </p>
      </section>

      <section aria-labelledby="report-section-5" className="report-preview-section">
        <h2 id="report-section-5">5. {t('Exam Summary')}</h2>
        <dl className="report-exam-summary">
          <div>
            <dt>{t('Independently scorable questions')}</dt>
            <dd>{examSummary.scorableQuestionCount}</dd>
          </div>
          <div>
            <dt>{t('Declared total marks')}</dt>
            <dd>{examSummary.declaredTotal ?? '—'}</dd>
          </div>
          <div>
            <dt>{t('Calculated total marks')}</dt>
            <dd>{examSummary.calculatedTotal ?? '—'}</dd>
          </div>
          <div>
            <dt>{t('Supporting materials')}</dt>
            <dd>{examSummary.materialCount}</dd>
          </div>
          <div>
            <dt>{t('Missing or ambiguous references')}</dt>
            <dd>{examSummary.missingOrAmbiguousReferenceCount}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="report-section-6" className="report-preview-section">
        <h2 id="report-section-6">6. {t('CLO Analysis')}</h2>
        <div className="ui-responsive-table">
          <table>
            <caption className="visually-hidden">{t('CLO Analysis')}</caption>
            <thead>
              <tr>
                <th scope="col">{t('CLO')}</th>
                <th scope="col">{t('CLO text')}</th>
                <th scope="col">{t('Linked questions')}</th>
                <th scope="col">{t('Total marks')}</th>
                <th scope="col">{t('Coverage status')}</th>
              </tr>
            </thead>
            <tbody>
              {clos.map((clo) => {
                const matches = relatedRows(rows, clo, 'clo')
                const judgments = matches.flatMap((row) => matchingJudgments(row, clo, 'clo'))
                const orderedReferences = sortQuestionReferences(
                  matches.map((row) => row.questionReference),
                  questions,
                )
                return (
                  <tr key={clo.id}>
                    <th scope="row">
                      <bdi>{clo.code}</bdi>
                    </th>
                    <td dir="auto">{clo.text}</td>
                    <td>{orderedReferences.join(', ') || t('None')}</td>
                    <td>{totalMarksForRecord(rows, clo, 'clo')}</td>
                    <td>
                      <StatusBadge status={coverageStatus(judgments)} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="report-section-7" className="report-preview-section">
        <h2 id="report-section-7">7. {t('Topic Analysis')}</h2>
        <div className="ui-responsive-table">
          <table>
            <caption className="visually-hidden">{t('Topic Analysis')}</caption>
            <thead>
              <tr>
                <th scope="col">{t('Course Topic')}</th>
                <th scope="col">{t('Linked questions')}</th>
                <th scope="col">{t('Total marks')}</th>
                <th scope="col">{t('Coverage status')}</th>
              </tr>
            </thead>
            <tbody>
              {topics.map((topic) => {
                const matches = relatedRows(rows, topic, 'topic')
                const judgments = matches.flatMap((row) =>
                  matchingJudgments(row, topic, 'topic'),
                )
                const orderedReferences = sortQuestionReferences(
                  matches.map((row) => row.questionReference),
                  questions,
                )
                return (
                  <tr key={topic.id}>
                    <th scope="row" dir="auto">
                      {topic.text}
                    </th>
                    <td>{orderedReferences.join(', ') || t('None')}</td>
                    <td>{totalMarksForRecord(rows, topic, 'topic')}</td>
                    <td>
                      <StatusBadge status={coverageStatus(judgments)} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="report-section-8" className="report-preview-section">
        <h2 id="report-section-8">8. {t('Marks & Structure')}</h2>
        <ul className="report-check-list">
          {findings
            .filter((finding) =>
              ['Marks and Totals', 'Numbering and Structure'].includes(finding.dimension),
            )
            .map((finding) => (
              <li key={finding.id}>
                <div className="drawer-finding-header">
                  <strong>
                    {presentRequirementName(finding.requirement_id, finding.requirement_name, locale)}
                  </strong>
                  <StatusBadge status={finding.status} />
                </div>
                <p dir="auto">{presentFindingExplanation(finding, locale)}</p>
              </li>
            ))}
        </ul>
      </section>

      <section aria-labelledby="report-section-9" className="report-preview-section">
        <h2 id="report-section-9">9. {t('Materials & References')}</h2>
        <div className="ui-responsive-table">
          <table>
            <caption className="visually-hidden">{t('Materials & References')}</caption>
            <thead>
              <tr>
                <th scope="col">{t('Question')}</th>
                <th scope="col">{t('Referenced item')}</th>
                <th scope="col">{t('Relationship result')}</th>
                <th scope="col">{t('Page')}</th>
              </tr>
            </thead>
            <tbody>
              {materialReferences.map((relationship) => (
                <tr key={relationship.reference.id}>
                  <td>
                    <bdi>
                      {questions.find((q) => q.id === relationship.reference.question_id)
                        ?.number_label ?? t('Unknown question')}
                    </bdi>
                  </td>
                  <td dir="auto">
                    <bdi dir="auto">{relationship.reference.original_text}</bdi>
                  </td>
                  <td>{t(RESULT_LABELS[relationship.result])}</td>
                  <td>{relationship.reference.page_number}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section aria-labelledby="report-section-10" className="report-preview-section">
        <h2 id="report-section-10">10. {t('Key Findings')}</h2>
        {(
          [
            ['Strengths', grouped.strengths],
            ['Areas for Improvement', grouped.areasForImprovement],
          ] as const
        ).map(([label, items]) => (
          <div key={label} className="report-finding-group">
            <h3>{t(label)}</h3>
            {items.length === 0 ? (
              <p>{t('None')}</p>
            ) : (
              <ul className="report-check-list">
                {items.map((finding) => (
                  <li key={finding.id}>
                    <div className="drawer-finding-header">
                      <strong>
                        {presentRequirementName(
                          finding.requirement_id,
                          finding.requirement_name,
                          locale,
                        )}
                      </strong>
                      <StatusBadge status={finding.status} />
                    </div>
                    <p dir="auto">{presentFindingExplanation(finding, locale)}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </section>

      <section aria-labelledby="report-section-11" className="report-preview-section">
        <h2 id="report-section-11">11. {t('Missing or Unverified Evidence')}</h2>
        {grouped.missingEvidence.length === 0 ? (
          <p>{t('None')}</p>
        ) : (
          <ul className="report-check-list">
            {grouped.missingEvidence.map((finding) => (
              <li key={finding.id}>
                <div className="drawer-finding-header">
                  <strong>
                    {presentRequirementName(finding.requirement_id, finding.requirement_name, locale)}
                  </strong>
                  <StatusBadge status={finding.status} />
                </div>
                <p dir="auto">{presentFindingExplanation(finding, locale)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="report-section-12" className="report-preview-section">
        <h2 id="report-section-12">12. {t('Recommendations')}</h2>
        {recommendationGroups.length === 0 ? (
          <p>{t('None')}</p>
        ) : (
          recommendationGroups.map((group) => (
            <div key={group.section} className="report-finding-group">
              <h3>{t(group.label)}</h3>
              <ol>
                {group.findings.map((finding) => (
                  <li key={finding.id} dir="auto">
                    {presentRequirementName(finding.requirement_id, finding.requirement_name, locale)}
                    {': '}
                    {t(scoreImpactMessage(finding.status))}
                  </li>
                ))}
              </ol>
            </div>
          ))
        )}
      </section>

      <section aria-labelledby="report-section-13" className="report-preview-section">
        <h2 id="report-section-13">13. {t('Scope Disclaimer')}</h2>
        <p>
          {t(
            'This report applies only to the uploaded examination and the corresponding Course Specification. The platform does not issue accreditation decisions, does not evaluate the complete academic program, and does not replace academic judgment. The faculty member remains responsible for the final examination decision.',
          )}
        </p>
      </section>



      <footer className="report-preview-footer">
        <Link to={`/analyses/${analysisId}/results/overview`}>{t('View Analysis')}</Link>
      </footer>
    </div>
  )
}
