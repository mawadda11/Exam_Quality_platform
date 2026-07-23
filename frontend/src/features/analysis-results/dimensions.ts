/** Literal Dimension values from 04_requirements.xlsx (surfaced on
 * FindingResponse.dimension) - used to route findings to the right PRD
 * Results-interface section without the frontend hardcoding a second copy
 * of which Requirement_IDs belong to which dimension. */
export const ALIGNMENT_COVERAGE_DIMENSIONS = new Set([
  'CLO Alignment',
  'CLO Coverage',
  'Topic Alignment',
  'Topic Coverage',
])

export const MARKS_STRUCTURE_DIMENSIONS = new Set(['Marks and Totals', 'Numbering and Structure'])
