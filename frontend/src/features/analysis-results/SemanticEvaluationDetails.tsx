import { useI18n } from '../../i18n/I18nProvider'
import { OriginalTextDisclosure } from '../../components/ui/OriginalTextDisclosure'
import type {
  FindingEvidenceRef,
  FindingItemJudgmentDetails,
  FindingResponse,
} from '../../types/api'
import { StatusBadge } from './StatusBadge'

function EvidenceReference({ evidence }: { evidence: FindingEvidenceRef }) {
  const { t } = useI18n()
  const source = evidence.source_document === 'exam' ? t('Exam') : 'TP-153'
  return (
    <span className="semantic-evidence-reference">
      <bdi dir="auto">
        {evidence.item_reference} · {source} {t('page')} {evidence.page_number} ·{' '}
        {evidence.evidence_type}
      </bdi>
    </span>
  )
}

function MissingEvidenceReference({ evidenceId }: { evidenceId: string }) {
  const { t } = useI18n()
  return (
    <span className="semantic-evidence-reference semantic-evidence-reference--missing">
      {t('Evidence reference unavailable in this response')}: <bdi>{evidenceId}</bdi>
    </span>
  )
}

interface ItemJudgmentProps {
  judgment: FindingItemJudgmentDetails
  evidenceById: ReadonlyMap<string, FindingEvidenceRef>
  relationshipRule: boolean
}

function ItemJudgment({ judgment, evidenceById, relationshipRule }: ItemJudgmentProps) {
  const { locale, t } = useI18n()
  const source = evidenceById.get(judgment.source_evidence_id)
  const targets = judgment.target_evidence_ids.map((id) => ({
    id,
    evidence: evidenceById.get(id),
  }))
  const isDerivedRelationship = relationshipRule && targets.length > 0

  return (
    <li className="semantic-item-judgment">
      <div className="semantic-item-judgment-header">
        <strong>
          {t(
            isDerivedRelationship
              ? 'Derived advisory relationship'
              : 'Governed semantic item judgment',
          )}
        </strong>
        <StatusBadge status={judgment.status} />
      </div>
      {isDerivedRelationship && (
        <p className="semantic-derived-notice">
          {t(
            'This relationship is an analysis output. It is not an official TP-153 mapping and does not overwrite source evidence.',
          )}
        </p>
      )}
      <dl className="semantic-item-evidence">
        <div>
          <dt>{t('Source evidence')}</dt>
          <dd>
            {source ? (
              <EvidenceReference evidence={source} />
            ) : (
              <MissingEvidenceReference evidenceId={judgment.source_evidence_id} />
            )}
          </dd>
        </div>
        <div>
          <dt>
            {t(isDerivedRelationship ? 'Related controlled evidence' : 'Target evidence')}
          </dt>
          <dd>
            {targets.length === 0 ? (
              <span>{t('No target relationship was asserted.')}</span>
            ) : (
              <ul className="semantic-target-list">
                {targets.map(({ id, evidence }) => (
                  <li key={id}>
                    {evidence ? (
                      <EvidenceReference evidence={evidence} />
                    ) : (
                      <MissingEvidenceReference evidenceId={id} />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </dd>
        </div>
      </dl>
      <p className="semantic-item-reasoning">
        <strong>{t('Concise reasoning')}:</strong>{' '}
        {locale === 'ar'
          ? t('The linked evidence supports the item-level judgment shown above.')
          : judgment.reasoning}
      </p>
      <OriginalTextDisclosure>{judgment.reasoning}</OriginalTextDisclosure>
    </li>
  )
}

export function SemanticEvaluationDetails({ finding }: { finding: FindingResponse }) {
  const { locale, t } = useI18n()
  const details = finding.evaluation_details
  if (!details) return null

  const evidenceById = new Map(finding.evidence.map((item) => [item.id, item]))
  const relationshipRule = finding.rule_id === 'RULE001' || finding.rule_id === 'RULE007'

  return (
    <div className="semantic-evaluation-details">
      <p className="semantic-reasoning">
        <strong>{t('Governed decision reasoning')}:</strong>{' '}
        {locale === 'ar'
          ? t('The decision is based on the governed requirement and the evidence linked below.')
          : details.reasoning}
      </p>
      <OriginalTextDisclosure>{details.reasoning}</OriginalTextDisclosure>

      {details.confidence_basis.length > 0 && (
        <div className="semantic-confidence-basis">
          <strong>{t('Confidence basis')}</strong>
          <ul>
            {details.confidence_basis.map((basis) => (
              <li key={basis}>
                {locale === 'ar' ? t('Confidence reflects the quality and completeness of the linked evidence.') : basis}
                <OriginalTextDisclosure>{basis}</OriginalTextDisclosure>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="semantic-item-judgments-section">
        <strong>
          {t('Evidence-linked item judgments')} ({details.item_judgments.length})
        </strong>
        {details.item_judgments.length === 0 ? (
          <p className="results-supporting-text">
            {t('No item-level relationship or judgment was retained for this finding.')}
          </p>
        ) : (
          <ol className="semantic-item-judgments">
            {details.item_judgments.map((judgment, index) => (
              <ItemJudgment
                key={`${judgment.source_evidence_id}-${index}`}
                judgment={judgment}
                evidenceById={evidenceById}
                relationshipRule={relationshipRule}
              />
            ))}
          </ol>
        )}
      </div>

      {details.retrieved_knowledge_ids.length > 0 && (
        <p className="semantic-kb-references">
          {t('Controlled KB references')}:{' '}
          {details.retrieved_knowledge_ids.map((id, index) => (
            <span key={id}>
              {index > 0 && ', '}
              <bdi>{id}</bdi>
            </span>
          ))}
        </p>
      )}
    </div>
  )
}
