import type {
  FindingEvidenceRef,
  FindingItemJudgmentDetails,
  FindingResponse,
} from '../../types/api'
import { StatusBadge } from './StatusBadge'

function evidenceLabel(evidence: FindingEvidenceRef): string {
  const source = evidence.source_document === 'exam' ? 'Exam' : 'TP-153'
  return `${evidence.item_reference} · ${source} page ${evidence.page_number} · ${evidence.evidence_type}`
}

function MissingEvidenceReference({ evidenceId }: { evidenceId: string }) {
  return (
    <span className="semantic-evidence-reference semantic-evidence-reference--missing">
      Evidence reference unavailable in this response: <bdi>{evidenceId}</bdi>
    </span>
  )
}

function EvidenceReference({ evidence }: { evidence: FindingEvidenceRef }) {
  return (
    <span className="semantic-evidence-reference">
      <bdi dir="auto">{evidenceLabel(evidence)}</bdi>
    </span>
  )
}

interface ItemJudgmentProps {
  judgment: FindingItemJudgmentDetails
  evidenceById: ReadonlyMap<string, FindingEvidenceRef>
  relationshipRule: boolean
}

function ItemJudgment({
  judgment,
  evidenceById,
  relationshipRule,
}: ItemJudgmentProps) {
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
          {isDerivedRelationship
            ? 'AI-derived advisory relationship'
            : 'Governed semantic item judgment'}
        </strong>
        <StatusBadge status={judgment.status} />
      </div>
      {isDerivedRelationship && (
        <p className="semantic-derived-notice">
          This relationship is an analysis output. It is not an official TP-153 mapping and does
          not overwrite source evidence.
        </p>
      )}
      <dl className="semantic-item-evidence">
        <div>
          <dt>Source evidence</dt>
          <dd>
            {source ? (
              <EvidenceReference evidence={source} />
            ) : (
              <MissingEvidenceReference evidenceId={judgment.source_evidence_id} />
            )}
          </dd>
        </div>
        <div>
          <dt>{isDerivedRelationship ? 'Related controlled evidence' : 'Target evidence'}</dt>
          <dd>
            {targets.length === 0 ? (
              <span>No target relationship was asserted.</span>
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
      <p className="semantic-item-reasoning" dir="auto">
        <strong>Concise reasoning:</strong> {judgment.reasoning}
      </p>
    </li>
  )
}

export function SemanticEvaluationDetails({ finding }: { finding: FindingResponse }) {
  const details = finding.evaluation_details
  if (!details) return null

  const evidenceById = new Map(finding.evidence.map((item) => [item.id, item]))
  const relationshipRule = finding.rule_id === 'RULE001' || finding.rule_id === 'RULE007'

  return (
    <div className="semantic-evaluation-details">
      <p className="semantic-reasoning" dir="auto">
        <strong>Governed decision reasoning:</strong> {details.reasoning}
      </p>

      {details.confidence_basis.length > 0 && (
        <div className="semantic-confidence-basis">
          <strong>Confidence basis</strong>
          <ul>
            {details.confidence_basis.map((basis) => (
              <li key={basis} dir="auto">
                {basis}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="semantic-item-judgments-section">
        <strong>Evidence-linked item judgments ({details.item_judgments.length})</strong>
        {details.item_judgments.length === 0 ? (
          <p className="results-supporting-text">
            No item-level relationship or judgment was retained for this finding.
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
          Controlled KB references:{' '}
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
