export function isPdfFile(file: File): boolean {
  return file.name.toLowerCase().endsWith('.pdf')
}

export interface AnalysisDetailsInput {
  courseCode: string
  courseName: string
  examType: string
  term: string
}

export interface AnalysisDetailsErrors {
  courseCode?: string
  courseName?: string
  examType?: string
  term?: string
}

export function validateAnalysisDetails(input: AnalysisDetailsInput): AnalysisDetailsErrors {
  const errors: AnalysisDetailsErrors = {}
  if (!input.courseCode.trim()) errors.courseCode = 'Course code is required.'
  if (!input.courseName.trim()) errors.courseName = 'Course name is required.'
  if (!input.examType.trim()) errors.examType = 'Select Midterm or Final.'
  if (!input.term.trim()) errors.term = 'Term is required.'
  return errors
}
