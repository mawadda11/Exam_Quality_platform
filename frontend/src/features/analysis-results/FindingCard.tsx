import {
  presentFindingExplanation,
  presentRecommendation,
  presentRequirementName,
} from '../../i18n/governedPresentation'
import { useI18n } from '../../i18n/I18nProvider'
import type {
  FindingEvidenceRef,
  FindingResponse,
  RecommendationResponse,
} from '../../types/api'
import { sortEvidenceReferences } from './facultyOrdering'
import {
  scoreImpactMessage,
  sectionDestinationForFinding,
} from './findingPresentation'
import type { EvidenceLookups } from './lookups'
import { StatusBadge } from './StatusBadge'

interface FindingCardProps {
  finding: FindingResponse
  lookups: EvidenceLookups
  recommendations?: RecommendationResponse[]
  showSpecializedLink?: boolean
  showDirectEvidence?: boolean
}

const MARKS_EVIDENCE_TYPES = new Set([
  'marks',
  'declared_total',
  'calculated_total',
  'marks_difference',
])

const MATERIAL_EVIDENCE_TYPES = new Set([
  'explicit_reference',
  'document_reference',
  'figure',
  'table',
  'code_block',
  'caption',
  'label',
  'supporting_material',
])

function directEvidence(
  finding: FindingResponse,
  destination: ReturnType<typeof sectionDestinationForFinding>,
  lookups: EvidenceLookups,
): FindingEvidenceRef[] {
  const types =
    destination?.section === 'marks-structure'
      ? MARKS_EVIDENCE_TYPES
      : destination?.section === 'supporting-evidence'
        ? MATERIAL_EVIDENCE_TYPES
        : null
  if (!types) return []
  return sortEvidenceReferences(
    finding.evidence.filter((evidence) => types.has(evidence.evidence_type)),
    [...lookups.questionByLabel.values()],
  )
}

function evidenceLabel(evidenceType: string): string {
  switch (evidenceType) {
    case 'declared_total':
      return 'Declared total marks'
    case 'calculated_total':
      return 'Calculated total marks'
    case 'marks_difference':
      return 'Difference between totals'
    case 'marks':
      return 'Question marks'
    case 'explicit_reference':
    case 'document_reference':
      return 'Referenced item'
    case 'figure':
      return 'Figure'
    case 'table':
      return 'Table'
    case 'code_block':
      return 'Code block'
    case 'caption':
      return 'Caption'
    case 'label':
      return 'Label'
    default:
      return 'Supporting material'
  }
}

function CompactDirectEvidence({
  evidence,
}: {
  evidence: FindingEvidenceRef[]
}) {
  const { t } = useI18n()
  return (
    <details className="finding-direct-evidence">
      <summary>{t('View direct evidence')}</summary>
      <ul>
        {evidence.map((item) => (
          <li key={item.id}>
            <strong>{t(evidenceLabel(item.evidence_type))}:</strong>{' '}
            <bdi>{item.item_reference}</bdi>
            <small>
              {t(item.source_document === 'exam' ? 'Exam' : 'Course Specification')}
              {`, ${t('page')} ${item.page_number}`}
            </small>
          </li>
        ))}
      </ul>
    </details>
  )
}

export function FindingCard({
  finding,
  lookups,
  recommendations = [],
  showSpecializedLink = true,
  showDirectEvidence = true,
}: FindingCardProps) {
  const { locale, t } = useI18n()
  const destination = sectionDestinationForFinding(finding)
  const evidence = showDirectEvidence
    ? directEvidence(finding, destination, lookups)
    : []

  return (
    <li className="finding-card">
      <div className="finding-card-header">
        <strong>
          {presentRequirementName(
            finding.requirement_id,
            finding.requirement_name,
            locale,
          )}
        </strong>
        <StatusBadge status={finding.status} />
      </div>

      <div className="finding-primary-summary">
        <p dir="auto">
          <strong>{t('Reason for the result')}:</strong>{' '}
          {presentFindingExplanation(finding, locale)}
        </p>
        <p className="finding-score-impact">
          <strong>{t('Score impact')}:</strong>{' '}
          {t(scoreImpactMessage(finding.status))}
        </p>
      </div>

      {recommendations.length > 0 && (
        <div className="finding-recommendations">
          <strong>{t('Recommendation')}</strong>
          <ul className="recommendation-list">
            {recommendations.map((recommendation) => {
              const presented = presentRecommendation(recommendation, locale)
              return (
                <li key={recommendation.recommendation_id}>
                  <strong>{presented.title}</strong>
                  <p>{presented.text}</p>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {destination && showSpecializedLink && (
        <a
          className="finding-specialized-link"
          href={`/analyses/${finding.analysis_id}/results/${destination.section}`}
        >
          {t(destination.label)}
        </a>
      )}

      {showDirectEvidence && evidence.length > 0 && (
        <CompactDirectEvidence evidence={evidence} />
      )}
    </li>
  )
}
