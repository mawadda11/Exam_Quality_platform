import type { AcademicStatus, FindingResponse } from '../../types/api'
import {
  ALIGNMENT_COVERAGE_DIMENSIONS,
  MARKS_STRUCTURE_DIMENSIONS,
} from './dimensions'

const SCORE_IMPACT_MESSAGES: Record<AcademicStatus, string> = {
  Satisfied: 'Included fully in the score.',
  'Partially Satisfied': 'Included with partial credit.',
  'Not Satisfied': 'Included as an unmet requirement.',
  'Not Verified':
    'Excluded because the evidence was insufficient for a reliable judgment.',
  'Not Applicable':
    'Excluded because the requirement does not apply to this analysis.',
}

export const FINDING_STATUSES: readonly AcademicStatus[] = [
  'Satisfied',
  'Partially Satisfied',
  'Not Satisfied',
  'Not Verified',
  'Not Applicable',
]

export const ATTENTION_STATUSES = new Set<AcademicStatus>([
  'Partially Satisfied',
  'Not Satisfied',
  'Not Verified',
])

export function scoreImpactMessage(status: AcademicStatus): string {
  return SCORE_IMPACT_MESSAGES[status]
}

export function countFindingStatuses(
  findings: FindingResponse[],
): Map<AcademicStatus, number> {
  const counts = new Map<AcademicStatus, number>(
    FINDING_STATUSES.map((status) => [status, 0]),
  )
  for (const finding of findings) {
    counts.set(finding.status, (counts.get(finding.status) ?? 0) + 1)
  }
  return counts
}

export function isRelationshipFinding(finding: FindingResponse): boolean {
  return finding.rule_id === 'RULE001' || finding.rule_id === 'RULE007'
}

const ATTENTION_ORDER: Record<AcademicStatus, number> = {
  'Not Satisfied': 0,
  'Partially Satisfied': 1,
  'Not Verified': 2,
  Satisfied: 3,
  'Not Applicable': 4,
}

export function sortFindingsForFaculty(
  findings: FindingResponse[],
): FindingResponse[] {
  return [...findings].sort(
    (left, right) =>
      ATTENTION_ORDER[left.status] - ATTENTION_ORDER[right.status],
  )
}

export interface FindingSectionDestination {
  section:
    | 'alignment-coverage'
    | 'marks-structure'
    | 'supporting-evidence'
  label: string
}

const SUPPORTING_EVIDENCE_RULES = new Set(['RULE014', 'RULE016', 'RULE022'])

export function sectionDestinationForFinding(
  finding: FindingResponse,
): FindingSectionDestination | null {
  if (
    ALIGNMENT_COVERAGE_DIMENSIONS.has(finding.dimension) ||
    finding.dimension === 'Assessment Alignment' ||
    finding.rule_id === 'RULE003'
  ) {
    return {
      section: 'alignment-coverage',
      label: 'View details in Alignment & Coverage',
    }
  }
  if (MARKS_STRUCTURE_DIMENSIONS.has(finding.dimension)) {
    return {
      section: 'marks-structure',
      label: 'View details in Marks & Structure',
    }
  }
  if (SUPPORTING_EVIDENCE_RULES.has(finding.rule_id)) {
    return {
      section: 'supporting-evidence',
      label: 'View details in Materials & References',
    }
  }
  return null
}
