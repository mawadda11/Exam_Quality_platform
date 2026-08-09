import { useState } from 'react'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { useI18n } from '../../i18n/I18nProvider'
import type {
  AcademicStatus,
  FindingResponse,
  RecommendationResponse,
} from '../../types/api'
import {
  EMPTY_FINDING_FILTERS,
  filterFindings,
  type FindingFilterValues,
} from './findingFilterModel'
import { FindingFilters } from './FindingFilters'
import { FindingCard } from './FindingCard'
import {
  ATTENTION_STATUSES,
  countFindingStatuses,
  FINDING_STATUSES,
  sortFindingsForFaculty,
} from './findingPresentation'
import type { EvidenceLookups } from './lookups'
import { MethodologyLink } from './MethodologyLink'
import { StatusBadge } from './StatusBadge'
import type { ResultResource } from './useAnalysisResultsData'

interface FindingsRecommendationsSectionProps {
  findings: FindingResponse[]
  recommendations: ResultResource<RecommendationResponse[]>
  recommendationsByFinding: Map<string, RecommendationResponse[]>
  lookups: EvidenceLookups
  onRetryRecommendations: () => void
}

function statusFindings(
  findings: FindingResponse[],
  status: AcademicStatus,
): FindingResponse[] {
  return findings.filter((finding) => finding.status === status)
}

export function FindingsRecommendationsSection({
  findings,
  recommendations,
  recommendationsByFinding,
  lookups,
  onRetryRecommendations,
}: FindingsRecommendationsSectionProps) {
  const { t } = useI18n()
  const [filters, setFilters] = useState<FindingFilterValues>(
    EMPTY_FINDING_FILTERS,
  )
  const visibleFindings = findings
  const filteredFindings = filterFindings(visibleFindings, filters)
  const counts = countFindingStatuses(visibleFindings)
  const missingEvidenceCount = counts.get('Not Verified') ?? 0
  const attention = sortFindingsForFaculty(
    filteredFindings.filter((finding) =>
      ATTENTION_STATUSES.has(finding.status),
    ),
  )
  const satisfied = statusFindings(filteredFindings, 'Satisfied')
  const notApplicable = statusFindings(filteredFindings, 'Not Applicable')

  function renderCards(items: FindingResponse[]) {
    return (
      <ul className="finding-list">
        {items.map((finding) => (
          <FindingCard
            key={finding.id}
            finding={finding}
            lookups={lookups}
            recommendations={recommendationsByFinding.get(finding.id)}
          />
        ))}
      </ul>
    )
  }

  return (
    <div className="findings-recommendations-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Findings & Recommendations')}</h2>
          <p>
            {t(
              'Review results requiring attention first, then open supporting evidence when needed.',
            )}
          </p>
        </div>
      </div>

      <div className="results-methodology-note">
        <p>
          {t(
            'Results use confirmed evidence, rule-based checks, and semantic analysis when needed. The complete methodology is available in Methodology & Help.',
          )}
        </p>
        <MethodologyLink
          anchor="evaluation-methods"
          label="How does the platform determine results?"
        />
      </div>

      {visibleFindings.length > 0 && (
        <>
          <ul
            className="finding-status-summary"
            aria-label={t('Finding status summary')}
          >
            {FINDING_STATUSES.filter(
              (status) =>
                status !== 'Not Applicable' || (counts.get(status) ?? 0) > 0,
            ).map((status) => (
              <li key={status}>
                <strong>{counts.get(status) ?? 0}</strong>
                <StatusBadge status={status} />
              </li>
            ))}
          </ul>
          <FindingFilters
            findings={visibleFindings}
            values={filters}
            resultCount={filteredFindings.length}
            onChange={setFilters}
          />
        </>
      )}

      {recommendations.status === 'loading' && (
        <div className="results-resource-state" role="status" aria-busy="true">
          {t('Loading recommendations…')}
        </div>
      )}
      {recommendations.status === 'error' && (
        <Alert variant="error" title={t('Could not load recommendations')}>
          <p>
            {t(
              'Findings remain available, but their recommendation records could not be loaded.',
            )}{' '}
            {recommendations.message}
          </p>
          <Button variant="secondary" onClick={onRetryRecommendations}>
            {t('Retry recommendations')}
          </Button>
        </Alert>
      )}

      {missingEvidenceCount > 0 && (
        <section className="missing-evidence-panel">
          <h3>
            {t('Insufficient Evidence — Excluded from the Score')} ({missingEvidenceCount})
          </h3>
          <p>
            {t(
              'The available evidence was insufficient for a reliable judgment, so these results were excluded from the score and were not treated as unmet requirements.',
            )}
          </p>
        </section>
      )}

      {visibleFindings.length === 0 ? (
        <p className="results-empty-state">{t('No findings are available.')}</p>
      ) : filteredFindings.length === 0 ? (
        <div className="results-empty-state" role="status">
          <p>{t('No findings match the selected filters.')}</p>
          <Button
            variant="secondary"
            onClick={() => setFilters(EMPTY_FINDING_FILTERS)}
          >
            {t('Reset filters')}
          </Button>
        </div>
      ) : (
        <div className="finding-priority-groups">
          {attention.length > 0 && (
            <section>
              <h3>{t('Requires attention')}</h3>
              {renderCards(attention)}
            </section>
          )}

          {satisfied.length > 0 && (
            <details className="finding-group-disclosure">
              <summary>
                {t('Satisfied findings ({count})', {
                  count: satisfied.length,
                })}
              </summary>
              {renderCards(satisfied)}
            </details>
          )}

          {notApplicable.length > 0 && (
            <details className="finding-group-disclosure">
              <summary>
                {t('Not Applicable findings ({count})', {
                  count: notApplicable.length,
                })}
              </summary>
              {renderCards(notApplicable)}
            </details>
          )}
        </div>
      )}
    </div>
  )
}
