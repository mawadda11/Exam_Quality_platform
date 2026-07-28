import { useState } from 'react'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { OriginalTextDisclosure } from '../../components/ui/OriginalTextDisclosure'
import {
  presentFindingExplanation,
  presentRequirementName,
} from '../../i18n/governedPresentation'
import { useI18n } from '../../i18n/I18nProvider'
import type { FindingResponse, RecommendationResponse } from '../../types/api'
import type { EvidenceLookupKind } from './EvidenceDrillDown'
import {
  EMPTY_FINDING_FILTERS,
  filterFindings,
  type FindingFilterValues,
} from './findingFilterModel'
import { FindingFilters } from './FindingFilters'
import { FindingCard } from './FindingCard'
import type { EvidenceLookups } from './lookups'
import type { ResultResource } from './useAnalysisResultsData'

interface FindingsRecommendationsSectionProps {
  findings: FindingResponse[]
  recommendations: ResultResource<RecommendationResponse[]>
  recommendationsByFinding: Map<string, RecommendationResponse[]>
  lookups: EvidenceLookups
  unavailableLookups?: ReadonlySet<EvidenceLookupKind>
  onRetryRecommendations: () => void
}

export function FindingsRecommendationsSection({
  findings,
  recommendations,
  recommendationsByFinding,
  lookups,
  unavailableLookups,
  onRetryRecommendations,
}: FindingsRecommendationsSectionProps) {
  const { locale, t } = useI18n()
  const [filters, setFilters] = useState<FindingFilterValues>(EMPTY_FINDING_FILTERS)
  const filteredFindings = filterFindings(findings, filters)
  const missingEvidence = filteredFindings.filter((finding) => finding.status === 'Not Verified')

  return (
    <div className="findings-recommendations-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Findings & Recommendations')}</h2>
          <p>{t('Filter the findings already returned for this analysis.')}</p>
        </div>
      </div>

      {findings.length > 0 && (
        <FindingFilters
          findings={findings}
          values={filters}
          resultCount={filteredFindings.length}
          onChange={setFilters}
        />
      )}

      {recommendations.status === 'loading' && (
        <div className="results-resource-state" role="status" aria-busy="true">
          {t('Loading recommendations…')}
        </div>
      )}
      {recommendations.status === 'error' && (
        <Alert variant="error" title={t('Could not load recommendations')}>
          <p>
            {t('Findings remain available, but their recommendation records could not be loaded.')}{' '}
            {recommendations.message}
          </p>
          <Button variant="secondary" onClick={onRetryRecommendations}>
            {t('Retry recommendations')}
          </Button>
        </Alert>
      )}

      {missingEvidence.length > 0 && (
        <div className="missing-evidence-panel">
          <h3>{t('Missing Evidence')} ({missingEvidence.length})</h3>
          <p>
            {t('These findings are excluded from the score because evidence was missing, unreadable, or insufficient—not because the exam failed the requirement.')}
          </p>
          <ul>
            {missingEvidence.map((finding) => (
              <li key={finding.id}>
                <strong>
                  {presentRequirementName(finding.requirement_id, finding.requirement_name, locale)}
                </strong>:{' '}
                <span>{presentFindingExplanation(finding, locale)}</span>
                <OriginalTextDisclosure>{finding.explanation}</OriginalTextDisclosure>
              </li>
            ))}
          </ul>
        </div>
      )}

      {findings.length === 0 ? (
        <p className="results-empty-state">{t('No findings are available.')}</p>
      ) : filteredFindings.length === 0 ? (
        <div className="results-empty-state" role="status">
          <p>{t('No findings match the selected filters.')}</p>
          <Button variant="secondary" onClick={() => setFilters(EMPTY_FINDING_FILTERS)}>
            {t('Reset filters')}
          </Button>
        </div>
      ) : (
        <ul className="finding-list">
          {filteredFindings.map((finding) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              lookups={lookups}
              unavailableLookups={unavailableLookups}
              recommendations={recommendationsByFinding.get(finding.id)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}
