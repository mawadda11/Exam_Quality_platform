import type {
  AcademicStatus,
  FindingEvidenceRef,
  FindingResponse,
  QuestionResponse,
} from '../../types/api'

/** Same worst-first precedence already used to prioritize findings in
 * Findings & Recommendations (see findingPresentation.ts's ATTENTION_ORDER)
 * - reused here to pick one representative status per question row. This
 * never invents a status: every value shown is a real FindingResponse.status
 * already returned by the backend for a finding that cites this question. */
const STATUS_SEVERITY: Record<AcademicStatus, number> = {
  'Not Satisfied': 0,
  'Partially Satisfied': 1,
  'Not Verified': 2,
  Satisfied: 3,
  'Not Applicable': 4,
}

export interface QuestionRow {
  question: QuestionResponse
  cloReferences: string[]
  topicReferences: string[]
  status: AcademicStatus | null
  findings: FindingResponse[]
  evidence: FindingEvidenceRef[]
}

function findingsForQuestion(
  question: QuestionResponse,
  findings: FindingResponse[],
): FindingResponse[] {
  return findings.filter((finding) =>
    finding.evidence.some((evidence) => evidence.item_reference === question.number_label),
  )
}

function worstStatus(findings: FindingResponse[]): AcademicStatus | null {
  if (findings.length === 0) return null
  return findings.reduce<AcademicStatus>(
    (worst, finding) =>
      STATUS_SEVERITY[finding.status] < STATUS_SEVERITY[worst] ? finding.status : worst,
    findings[0].status,
  )
}

/** Target item_references (CLO/topic codes) the given rule's item judgments
 * suggest for this question, deduplicated. Mirrors the source/target
 * evidence-citation join already used in AlignmentCoverageSection, applied
 * per-question for a compact badge list rather than a full relationship
 * table. */
function relationshipTargets(
  findings: FindingResponse[],
  question: QuestionResponse,
  ruleId: string,
): string[] {
  const references = new Set<string>()
  for (const finding of findings) {
    if (finding.rule_id !== ruleId || !finding.evaluation_details) continue
    const evidenceById = new Map(finding.evidence.map((item) => [item.id, item]))
    for (const judgment of finding.evaluation_details.item_judgments) {
      const source = evidenceById.get(judgment.source_evidence_id)
      if (source?.item_reference !== question.number_label) continue
      for (const targetId of judgment.target_evidence_ids) {
        const target = evidenceById.get(targetId)
        if (target) references.add(target.item_reference)
      }
    }
  }
  return [...references]
}

/**
 * Evidence belonging to a question: items directly citing the question itself,
 * plus judgment targets (CLO/topic/etc.) of judgments sourced from the question.
 * A shared finding's evidence array can span every question in the exam (e.g. total
 * marks totals), so this must never fall back to a finding's full evidence array.
 */
function evidenceForQuestion(
  question: QuestionResponse,
  relatedFindings: FindingResponse[],
): FindingEvidenceRef[] {
  const scoped = new Map<string, FindingEvidenceRef>()
  for (const finding of relatedFindings) {
    for (const item of finding.evidence) {
      if (item.item_reference === question.number_label) {
        scoped.set(item.id, item)
      }
    }
    if (!finding.evaluation_details) continue
    const evidenceById = new Map(finding.evidence.map((item) => [item.id, item]))
    for (const judgment of finding.evaluation_details.item_judgments) {
      const source = evidenceById.get(judgment.source_evidence_id)
      if (source?.item_reference !== question.number_label) continue
      for (const targetId of judgment.target_evidence_ids) {
        const target = evidenceById.get(targetId)
        if (target) scoped.set(target.id, target)
      }
    }
  }
  return [...scoped.values()]
}

export function buildQuestionRows(
  questions: QuestionResponse[],
  findings: FindingResponse[],
): QuestionRow[] {
  return questions.map((question) => {
    const related = findingsForQuestion(question, findings)
    return {
      question,
      cloReferences: relationshipTargets(findings, question, 'RULE001'),
      topicReferences: relationshipTargets(findings, question, 'RULE007'),
      status: worstStatus(related),
      findings: related,
      evidence: evidenceForQuestion(question, related),
    }
  })
}

export interface QuestionFilterValues {
  search: string
  status: AcademicStatus | ''
  clo: string
  topic: string
}

export const EMPTY_QUESTION_FILTERS: QuestionFilterValues = {
  search: '',
  status: '',
  clo: '',
  topic: '',
}

export function filterQuestionRows(
  rows: QuestionRow[],
  filters: QuestionFilterValues,
): QuestionRow[] {
  const search = filters.search.trim().toLocaleLowerCase()
  return rows.filter((row) => {
    if (search) {
      const haystack =
        `${row.question.number_label} ${row.question.question_text}`.toLocaleLowerCase()
      if (!haystack.includes(search)) return false
    }
    if (filters.status && row.status !== filters.status) return false
    if (filters.clo && !row.cloReferences.includes(filters.clo)) return false
    if (filters.topic && !row.topicReferences.includes(filters.topic)) return false
    return true
  })
}
