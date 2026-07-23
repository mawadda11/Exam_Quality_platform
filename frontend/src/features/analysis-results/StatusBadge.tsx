import type { AcademicStatus } from '../../types/api'

const STATUS_CLASS: Record<AcademicStatus, string> = {
  Satisfied: 'status-badge status-satisfied',
  'Partially Satisfied': 'status-badge status-partial',
  'Not Satisfied': 'status-badge status-not-satisfied',
  'Not Verified': 'status-badge status-not-verified',
  'Not Applicable': 'status-badge status-not-applicable',
}

export function StatusBadge({ status }: { status: AcademicStatus }) {
  return <span className={STATUS_CLASS[status]}>{status}</span>
}

/** CLAUDE.md: "Do not present derived project rules as official
 * quotations." source_type is always "Derived Exam Requirement" or "System
 * Requirement" (04_requirements.xlsx) - never itself an official standard
 * quotation - so labelling it plainly is sufficient to honor that rule. */
export function GovernanceTag({ sourceType }: { sourceType: string }) {
  return (
    <span
      className="governance-tag"
      title="This requirement's official source classification, from the versioned knowledge base."
    >
      {sourceType}
    </span>
  )
}
