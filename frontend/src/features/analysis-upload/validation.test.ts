import { describe, expect, it } from 'vitest'
import { isPdfFile, validateAnalysisDetails } from './validation'

describe('isPdfFile', () => {
  it('accepts .pdf files case-insensitively', () => {
    expect(isPdfFile(new File([], 'Exam.PDF'))).toBe(true)
    expect(isPdfFile(new File([], 'exam.pdf'))).toBe(true)
  })

  it('rejects non-pdf files', () => {
    expect(isPdfFile(new File([], 'exam.txt'))).toBe(false)
    expect(isPdfFile(new File([], 'exam.pdf.exe'))).toBe(false)
  })
})

describe('validateAnalysisDetails', () => {
  it('flags every required field when all are empty', () => {
    const errors = validateAnalysisDetails({ courseCode: '', courseName: '', examType: '', term: '' })
    expect(errors).toEqual({
      courseCode: 'Course code is required.',
      courseName: 'Course name is required.',
      examType: 'Select Midterm or Final.',
      term: 'Term is required.',
    })
  })

  it('flags whitespace-only fields as empty', () => {
    const errors = validateAnalysisDetails({
      courseCode: '   ',
      courseName: 'Software Engineering',
      examType: 'Midterm',
      term: '2026 Spring',
    })
    expect(errors).toEqual({ courseCode: 'Course code is required.' })
  })

  it('returns no errors when all fields are filled', () => {
    const errors = validateAnalysisDetails({
      courseCode: 'CPIT-450',
      courseName: 'Software Engineering',
      examType: 'Midterm',
      term: '2026 Spring',
    })
    expect(errors).toEqual({})
  })
})
