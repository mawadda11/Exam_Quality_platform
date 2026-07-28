import { useI18n } from '../../i18n/I18nProvider'
import { OriginalTextDisclosure } from '../../components/ui/OriginalTextDisclosure'
import {
  presentFindingExplanation,
  presentGovernedLabel,
  presentRecommendation,
  presentRequirementName,
} from '../../i18n/governedPresentation'
import type { FindingResponse, RecommendationResponse } from '../../types/api'
import { EvidenceDrillDown, type EvidenceLookupKind } from './EvidenceDrillDown'
import type { EvidenceLookups } from './lookups'
import { SemanticConfidenceBadge } from './SemanticConfidenceBadge'
import { SemanticEvaluationDetails } from './SemanticEvaluationDetails'
import { GovernanceTag, StatusBadge } from './StatusBadge'

interface FindingCardProps {
  finding: FindingResponse
  lookups: EvidenceLookups
  recommendations?: RecommendationResponse[]
  unavailableLookups?: ReadonlySet<EvidenceLookupKind>
}

export function FindingCard({ finding, lookups, recommendations = [], unavailableLookups }: FindingCardProps) {
  const { locale, t } = useI18n()
  const isAiAssisted = finding.evaluator_type === 'semantic_ai'
  const hasAiProvenance = isAiAssisted && Boolean(
    finding.ai_provider || finding.ai_model || finding.prompt_template_version || finding.kb_version,
  )

  return (
    <li className="finding-card">
      <div className="finding-card-header">
        <strong>{presentRequirementName(finding.requirement_id, finding.requirement_name, locale)}</strong>
        <div className="finding-card-badges">
          {isAiAssisted && <span className="analysis-assisted-tag">{t('Analysis-assisted')}</span>}
          {finding.confidence_level && <SemanticConfidenceBadge level={finding.confidence_level} />}
          <StatusBadge status={finding.status} />
        </div>
      </div>
      <p className="finding-card-meta" dir="auto">
        {presentGovernedLabel(finding.dimension, locale)} · {t('Requirement')} <bdi>{finding.requirement_id}</bdi> · {t('Rule')}{' '}
        <bdi>{finding.rule_id}</bdi> · <GovernanceTag sourceType={finding.source_type} />
      </p>
      {hasAiProvenance && (
        <details className="finding-audit-details">
          <summary>{t('Audit details')}</summary>
          <p className="finding-ai-meta">
            {finding.ai_provider && <>{t('Provider')}: <bdi>{finding.ai_provider}</bdi></>}
            {finding.ai_model && <> · {t('Model')}: <bdi>{finding.ai_model}</bdi></>}
            {finding.prompt_template_version && <> · {t('Prompt')}: <bdi>{finding.prompt_template_version}</bdi></>}
            {finding.kb_version && <> · {t('KB')}: <bdi>{finding.kb_version}</bdi></>}
          </p>
        </details>
      )}
      <p>{presentFindingExplanation(finding, locale)}</p>
      <OriginalTextDisclosure>
        <p>{finding.explanation}</p>
      </OriginalTextDisclosure>
      {finding.evaluation_details && (
        <details className="semantic-evaluation-disclosure">
          <summary>{t('Semantic evaluation details')}</summary>
          <SemanticEvaluationDetails finding={finding} />
        </details>
      )}
      <details>
        <summary>{t('Evidence')} ({finding.evidence.length})</summary>
        <EvidenceDrillDown
          evidence={finding.evidence}
          status={finding.status}
          lookups={lookups}
          unavailableLookups={unavailableLookups}
        />
      </details>
      {recommendations.length > 0 && (
        <ul className="recommendation-list">
          {recommendations.map((rec) => {
            const presented = presentRecommendation(rec, locale)
            return (
              <li key={rec.recommendation_id}>
                <strong>{presented.title}</strong>
                <p>{presented.text}</p>
                <span className="recommendation-meta">
                  {presented.type} · {t('For')}: {presented.targetUser}
                </span>
                <OriginalTextDisclosure>
                  <strong>{rec.title}</strong>
                  <p>{rec.text}</p>
                </OriginalTextDisclosure>
              </li>
            )
          })}
        </ul>
      )}
    </li>
  )
}
