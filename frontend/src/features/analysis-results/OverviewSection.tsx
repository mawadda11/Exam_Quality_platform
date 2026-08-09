import { Card } from '../../components/ui/Card'
import { ScoreRing } from '../../components/ui/ScoreRing'
import { StatusBadge } from '../../components/ui/StatusBadge'
import type {
  AcademicStatus,
  AnalysisScoreResponse,
  RuleCoverageAuditResponse,
} from '../../types/api'
import { RuleCoveragePanel } from './RuleCoveragePanel'
import type { ResultResource } from './useAnalysisResultsData'
import { useI18n } from '../../i18n/I18nProvider'
import { MethodologyLink } from './MethodologyLink'

interface OverviewSectionProps {
  score: AnalysisScoreResponse
  ruleCoverage: ResultResource<RuleCoverageAuditResponse>
  onRetryRuleCoverage: () => void
}

function statusCounts(score: AnalysisScoreResponse): [AcademicStatus, number][] {
  return [
    ['Satisfied', score.satisfied_count],
    ['Partially Satisfied', score.partially_satisfied_count],
    ['Not Satisfied', score.not_satisfied_count],
    ['Not Verified', score.not_verified_count],
    ['Not Applicable', score.not_applicable_count],
  ]
}

export function OverviewSection({
  score,
  ruleCoverage,
  onRetryRuleCoverage,
}: OverviewSectionProps) {
  const { t } = useI18n()
  return (
    <div className="overview-section results-section-stack">
      <div className="results-section-heading">
        <div>
          <h2>{t('Overview')}</h2>
          <p>{t('A summary of the quality checks completed for this exam.')}</p>
        </div>
      </div>

      <div className="overview-summary-stack">
        <Card as="section" className="overview-status-card">
          <h3>{t('Evaluation results')}</h3>
          <ul className="status-count-grid">
            {statusCounts(score).map(([status, count]) => (
              <li key={status}>
                <strong>{count}</strong>
                <StatusBadge status={status} />
              </li>
            ))}
          </ul>
        </Card>

        <Card as="section" className="overview-score-card">
          <div className="overview-score-detail-grid">
            <div className="overview-score-ring-wrap">
              <ScoreRing
                score={score.score}
                denominator={score.denominator}
                emptyLabel={t(score.label ?? 'Insufficient Evidence')}
                label={
                  score.score_mode === 'local_preliminary'
                    ? t('Preliminary Local Quality Score')
                    : t('Overall Exam Quality Score')
                }
                denominatorKind={
                  score.score_mode === 'local_preliminary' ? 'applicable' : 'verified'
                }
              />
            </div>
            <div className="score-transparency">
              <h4>{t('About this score')}</h4>
              <p>
                {t('This is an advisory estimate of exam quality based on the criteria that could be verified. It is not the exam mark or a student pass rate.')}
              </p>
              {(score.excluded_local_semantic_count ?? 0) > 0 && (
                <p className="results-supporting-text">
                  {t('{count} local semantic suggestion(s) remain visible for review but are excluded from this preliminary score.', {
                    count: score.excluded_local_semantic_count ?? 0,
                  })}
                </p>
              )}
              <MethodologyLink anchor="overall-score" />
            </div>
          </div>
        </Card>
      </div>

      <RuleCoveragePanel coverage={ruleCoverage} onRetry={onRetryRuleCoverage} />
    </div>
  )
}
