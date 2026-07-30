import type {
  AcademicStatus,
  AnalysisScoreResponse,
  FindingResponse,
  QuestionResponse,
} from '../../types/api'
import {
  ATTENTION_STATUSES,
  sortFindingsForFaculty,
} from '../analysis-results/findingPresentation'
import { independentlyScorableQuestions } from '../analysis-results/facultyOrdering'
import type { MaterialRelationshipView } from '../analysis-results/materialRelationships'

/** RULE018 is the authoritative source for both displayed totals. The API's
 * compact evidence references intentionally omit extracted_text, so the web
 * report reads the two governed values from RULE018's persisted explanation
 * instead of inventing a separate marks calculation. */
export function marksTotalsFromFindings(findings: FindingResponse[]): {
  declared: number | null
  calculated: number | null
} {
  const marksFinding = findings.find((finding) => finding.rule_id === 'RULE018')
  if (!marksFinding) return { declared: null, calculated: null }

  const match = marksFinding.explanation.match(
    /Calculated total marks \(([-+]?\d+(?:\.\d+)?)\).*?declared total marks \(([-+]?\d+(?:\.\d+)?)\)/i,
  )
  if (match) {
    return {
      calculated: Number.parseFloat(match[1]),
      declared: Number.parseFloat(match[2]),
    }
  }

  // Defensive compatibility for historical fixtures that stored a numeric
  // declared total in item_reference. No calculated-total row is expected in
  // current analyses, so an absent governed explanation remains unknown.
  const declaredEvidence = marksFinding.evidence.find(
    (item) => item.evidence_type === 'declared_total',
  )
  const parsedDeclared = declaredEvidence
    ? Number.parseFloat(declaredEvidence.item_reference)
    : Number.NaN
  return {
    declared: Number.isFinite(parsedDeclared) ? parsedDeclared : null,
    calculated: null,
  }
}

export interface ExamSummary {
  scorableQuestionCount: number
  declaredTotal: number | null
  calculatedTotal: number | null
  materialCount: number
  missingOrAmbiguousReferenceCount: number
}

export function buildExamSummary(
  questions: QuestionResponse[],
  findings: FindingResponse[],
  materialCount: number,
  references: MaterialRelationshipView[],
): ExamSummary {
  const totals = marksTotalsFromFindings(findings)
  return {
    scorableQuestionCount: independentlyScorableQuestions(questions).length,
    declaredTotal: totals.declared,
    calculatedTotal: totals.calculated,
    materialCount,
    missingOrAmbiguousReferenceCount: references.filter(
      (reference) => reference.result === 'missing' || reference.result === 'ambiguous',
    ).length,
  }
}

export interface GroupedFindings {
  strengths: FindingResponse[]
  areasForImprovement: FindingResponse[]
  missingEvidence: FindingResponse[]
}

export function groupFindingsForReport(findings: FindingResponse[]): GroupedFindings {
  const missingEvidence = findings.filter((finding) => finding.status === 'Not Verified')
  const areasForImprovement = sortFindingsForFaculty(
    findings.filter(
      (finding) =>
        ATTENTION_STATUSES.has(finding.status) && finding.status !== 'Not Verified',
    ),
  )
  const strengths = findings.filter((finding) => finding.status === 'Satisfied')
  return { strengths, areasForImprovement, missingEvidence }
}

export interface RecommendationSectionGroup {
  section: 'questions' | 'alignment-coverage' | 'marks-structure' | 'supporting-evidence'
  label: string
  findings: FindingResponse[]
}

const SECTION_LABELS: Record<RecommendationSectionGroup['section'], string> = {
  questions: 'Questions',
  'alignment-coverage': 'Alignment & Coverage',
  'marks-structure': 'Marks & Structure',
  'supporting-evidence': 'Materials & References',
}

const CLARITY_DIMENSIONS = new Set(['Question Clarity', 'Question Completeness'])
const ALIGNMENT_DIMENSIONS = new Set([
  'CLO Alignment',
  'CLO Coverage',
  'Topic Alignment',
  'Topic Coverage',
])
const MARKS_DIMENSIONS = new Set(['Marks and Totals', 'Numbering and Structure'])
const SUPPORTING_EVIDENCE_RULES = new Set(['RULE014', 'RULE016', 'RULE022'])

function sectionForFinding(finding: FindingResponse): RecommendationSectionGroup['section'] | null {
  if (CLARITY_DIMENSIONS.has(finding.dimension)) return 'questions'
  if (ALIGNMENT_DIMENSIONS.has(finding.dimension)) return 'alignment-coverage'
  if (MARKS_DIMENSIONS.has(finding.dimension)) return 'marks-structure'
  if (SUPPORTING_EVIDENCE_RULES.has(finding.rule_id)) return 'supporting-evidence'
  return null
}

/** Recommendations are academic support text already returned per finding;
 * this only groups the findings that carry one under the four faculty
 * sections without duplicating near-identical entries for the same
 * requirement. */
export function groupRecommendationsForReport(
  findings: FindingResponse[],
): RecommendationSectionGroup[] {
  const withRecommendation = findings.filter(
    (finding) => finding.recommendation_id !== null && ATTENTION_STATUSES.has(finding.status),
  )
  const groups = new Map<RecommendationSectionGroup['section'], FindingResponse[]>()
  const seenRequirements = new Set<string>()
  for (const finding of withRecommendation) {
    const section = sectionForFinding(finding)
    if (!section) continue
    const dedupeKey = `${section}:${finding.requirement_id}`
    if (seenRequirements.has(dedupeKey)) continue
    seenRequirements.add(dedupeKey)
    const existing = groups.get(section) ?? []
    existing.push(finding)
    groups.set(section, existing)
  }
  return (Object.keys(SECTION_LABELS) as RecommendationSectionGroup['section'][])
    .filter((section) => groups.has(section))
    .map((section) => ({
      section,
      label: SECTION_LABELS[section],
      findings: groups.get(section) ?? [],
    }))
}

/** Executive-summary dimension lists are derived only from authoritative
 * findings already computed elsewhere (never invents strengths or
 * weaknesses beyond what the governed findings already state). */
export function strongestDimensions(strengths: FindingResponse[], limit = 3): string[] {
  return [...new Set(strengths.map((finding) => finding.dimension))].slice(0, limit)
}

export function weakestDimensions(
  areasForImprovement: FindingResponse[],
  limit = 3,
): string[] {
  return [...new Set(areasForImprovement.map((finding) => finding.dimension))].slice(0, limit)
}

export const STATUS_DISTRIBUTION_ORDER: readonly AcademicStatus[] = [
  'Satisfied',
  'Partially Satisfied',
  'Not Satisfied',
  'Not Verified',
  'Not Applicable',
]

export function statusDistributionCounts(
  score: AnalysisScoreResponse,
): Record<AcademicStatus, number> {
  return {
    Satisfied: score.satisfied_count,
    'Partially Satisfied': score.partially_satisfied_count,
    'Not Satisfied': score.not_satisfied_count,
    'Not Verified': score.not_verified_count,
    'Not Applicable': score.not_applicable_count,
  }
}

