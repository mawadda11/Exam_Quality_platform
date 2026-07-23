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

function describeEvidenceItem(item: FindingEvidenceRef, lookups: EvidenceLookups): string {
  const location = `${item.source_document === 'exam' ? 'Exam' : 'TP-153'} p.${item.page_number}`

  if (item.evidence_type === 'clo') {
    const clo = lookups.cloByCode.get(item.item_reference)
    return `CLO ${item.item_reference}${clo ? `: ${clo.text}` : ''} (${location})`
  }
  if (item.evidence_type === 'topic') {
    const topic = lookups.topicByCode.get(item.item_reference)
    return `Topic ${item.item_reference}${topic ? `: ${topic.text}` : ''} (${location})`
  }
  if (item.evidence_type === 'question_text') {
    const question = lookups.questionByLabel.get(item.item_reference)
    return `Question ${item.item_reference}${question ? `: ${question.question_text}` : ''} (${location})`
  }
  const label = EVIDENCE_TYPE_LABELS[item.evidence_type] ?? item.evidence_type
  return `${label}: ${item.item_reference} (${location})`
}

interface EvidenceDrillDownProps {
  evidence: FindingEvidenceRef[]
  status: AcademicStatus
  lookups: EvidenceLookups
}

/** Honest empty/degraded states (no invented data):
 * - Not Applicable with no evidence: expected, not a failure.
 * - Any other status with no evidence: a real absence, worth surfacing as
 *   such rather than showing a blank drill-down panel. */
export function EvidenceDrillDown({ evidence, status, lookups }: EvidenceDrillDownProps) {
  if (evidence.length === 0) {
    return (
      <p className="evidence-empty">
        {status === 'Not Applicable'
          ? 'No evidence is linked - this rule does not apply in this case.'
          : 'No evidence was linked to this finding.'}
      </p>
    )
  }

  return (
    <ul className="evidence-list">
      {evidence.map((item) => (
        <li key={item.id}>{describeEvidenceItem(item, lookups)}</li>
      ))}
    </ul>
  )
}
