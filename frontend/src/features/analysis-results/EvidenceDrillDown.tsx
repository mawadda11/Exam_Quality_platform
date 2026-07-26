import type { AcademicStatus, FindingEvidenceRef } from '../../types/api'
import type { EvidenceLookups } from './lookups'

const EVIDENCE_TYPE_LABELS: Record<string, string> = {
  question_text: 'Question text',
  marks: 'Marks',
  declared_total: 'Declared total',
  instructions: 'Instructions',
  clo: 'CLO citation',
  topic: 'Topic citation',
  assessment_record: 'Assessment record',
  missing_section: 'Missing section',
}

export type EvidenceLookupKind = 'clo' | 'topic' | 'question'

interface ResolvedEvidence {
  label: string
  sourceText: string | null
  lookupKind: EvidenceLookupKind | null
}

function resolveEvidence(
  item: FindingEvidenceRef,
  lookups: EvidenceLookups,
): ResolvedEvidence {
  if (item.evidence_type === 'clo') {
    return {
      label: 'CLO citation',
      sourceText: lookups.cloByCode.get(item.item_reference)?.text ?? null,
      lookupKind: 'clo',
    }
  }
  if (item.evidence_type === 'topic') {
    return {
      label: 'Topic citation',
      sourceText: lookups.topicByCode.get(item.item_reference)?.text ?? null,
      lookupKind: 'topic',
    }
  }
  if (item.evidence_type === 'question_text') {
    return {
      label: 'Question text',
      sourceText:
        lookups.questionByLabel.get(item.item_reference)?.question_text ?? null,
      lookupKind: 'question',
    }
  }
  return {
    label: EVIDENCE_TYPE_LABELS[item.evidence_type] ?? item.evidence_type,
    sourceText: null,
    lookupKind: null,
  }
}

interface EvidenceDrillDownProps {
  evidence: FindingEvidenceRef[]
  status: AcademicStatus
  lookups: EvidenceLookups
  unavailableLookups?: ReadonlySet<EvidenceLookupKind>
}

export function EvidenceDrillDown({
  evidence,
  status,
  lookups,
  unavailableLookups = new Set(),
}: EvidenceDrillDownProps) {
  if (evidence.length === 0) {
    return (
      <p className="evidence-empty">
        {status === 'Not Applicable'
          ? 'No evidence is linked — this rule does not apply in this case.'
          : 'No evidence was linked to this finding.'}
      </p>
    )
  }

  return (
    <ul className="evidence-list">
      {evidence.map((item) => {
        const resolved = resolveEvidence(item, lookups)
        const enrichmentUnavailable =
          resolved.lookupKind !== null && unavailableLookups.has(resolved.lookupKind)
        return (
          <li key={item.id} className="evidence-item">
            <dl>
              <div>
                <dt>Source</dt>
                <dd>{item.source_document === 'exam' ? 'Exam' : 'TP-153'}</dd>
              </div>
              <div>
                <dt>Page</dt>
                <dd>{item.page_number}</dd>
              </div>
              <div>
                <dt>Evidence type</dt>
                <dd>{resolved.label}</dd>
              </div>
              <div>
                <dt>Reference</dt>
                <dd>
                  <bdi dir="auto">{item.item_reference}</bdi>
                </dd>
              </div>
            </dl>
            {resolved.sourceText && (
              <p className="evidence-source-text" dir="auto">
                {resolved.sourceText}
              </p>
            )}
            {!resolved.sourceText && enrichmentUnavailable && (
              <p className="evidence-enrichment-note">
                Referenced source text is unavailable because its extracted-data request failed.
              </p>
            )}
          </li>
        )
      })}
    </ul>
  )
}
