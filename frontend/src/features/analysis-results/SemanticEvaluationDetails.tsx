import { useI18n } from '../../i18n/I18nProvider'
import type { FindingResponse } from '../../types/api'
import { isRelationshipFinding } from './findingPresentation'
import { SemanticConfidenceBadge } from './SemanticConfidenceBadge'

export function FacultyDeterminationDetails({
  finding,
}: {
  finding: FindingResponse
}) {
  const { t } = useI18n()
  const details = finding.evaluation_details
  const evaluatedItemCount =
    details?.item_judgments.length || finding.evidence.length

  return (
    <div className="faculty-determination-details">
      <dl>
        <div>
          <dt>{t('Evaluation approach')}</dt>
          <dd>
            {t(
              finding.evaluator_type === 'deterministic_rule'
                ? 'Rule-based automated check'
                : 'Semantic content analysis',
            )}
          </dd>
        </div>
        <div>
          <dt>{t('Evaluated items')}</dt>
          <dd>{evaluatedItemCount}</dd>
        </div>
        {finding.confidence_level && (
          <div>
            <dt>{t('Evidence reliability')}</dt>
            <dd>
              <SemanticConfidenceBadge level={finding.confidence_level} />
            </dd>
          </div>
        )}
        {isRelationshipFinding(finding) && (
          <div>
            <dt>{t('Relationship type')}</dt>
            <dd>{t('Suggested relationship')}</dd>
          </div>
        )}
      </dl>
      <p>
        {t(
          'The result uses the available evidence linked to this requirement. Evidence reliability describes confidence in the judgment, not the degree to which the requirement is satisfied.',
        )}
      </p>
      {isRelationshipFinding(finding) && (
        <p>
          {t(
            'This is an analytical suggestion for review, not an official mapping from the Course Specification.',
          )}
        </p>
      )}
    </div>
  )
}

export function SemanticEvaluationDetails({
  finding,
}: {
  finding: FindingResponse
}) {
  return <FacultyDeterminationDetails finding={finding} />
}
