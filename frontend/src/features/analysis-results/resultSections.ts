export type ResultsSectionId =
  | 'overview'
  | 'questions'
  | 'alignment-coverage'
  | 'marks-structure'
  | 'supporting-evidence'
  | 'findings-recommendations'
  | 'report'

export const RESULTS_SECTIONS: { id: ResultsSectionId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'questions', label: 'Questions' },
  { id: 'alignment-coverage', label: 'Alignment & Coverage' },
  { id: 'marks-structure', label: 'Marks & Structure' },
  { id: 'supporting-evidence', label: 'Materials & References' },
  { id: 'findings-recommendations', label: 'Findings & Recommendations' },
  { id: 'report', label: 'Report' },
]

export function isResultsSectionId(value: string | undefined): value is ResultsSectionId {
  return RESULTS_SECTIONS.some((section) => section.id === value)
}
