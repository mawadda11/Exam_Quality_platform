import { useState, type FormEvent } from 'react'
import { createAnalysis, getAnalysis } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type {
  AnalysisResponse,
  ExamType,
  ProcessingStage,
  UploadedFileResponse,
} from '../../types/api'
import { AnalysisResults } from '../analysis-results/AnalysisResults'
import { FileUploadField } from './FileUploadField'
import { ProcessingStatus } from './ProcessingStatus'
import { validateAnalysisDetails, type AnalysisDetailsErrors } from './validation'

const EXAM_TYPES: ExamType[] = ['Midterm', 'Final']

export function AnalysisUploadFlow() {
  const [courseCode, setCourseCode] = useState('')
  const [courseName, setCourseName] = useState('')
  const [examType, setExamType] = useState<ExamType | ''>('')
  const [term, setTerm] = useState('')
  const [errors, setErrors] = useState<AnalysisDetailsErrors>({})
  const [isCreating, setIsCreating] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [processingState, setProcessingState] = useState<ProcessingStage | null>(null)

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault()
    const validationErrors = validateAnalysisDetails({ courseCode, courseName, examType, term })
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return

    setIsCreating(true)
    setSubmitError(null)
    try {
      const created = await createAnalysis({
        course: { code: courseCode, name: courseName },
        exam_type: examType as ExamType,
        term,
      })
      setAnalysis(created)
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.detail : 'Could not create the analysis.')
    } finally {
      setIsCreating(false)
    }
  }

  function findUploaded(fileType: 'exam' | 'tp153'): UploadedFileResponse | undefined {
    return analysis?.uploaded_files.find((file) => file.file_type === fileType)
  }

  async function refreshAnalysis(): Promise<void> {
    if (!analysis) return
    const refreshed = await getAnalysis(analysis.id)
    setAnalysis(refreshed)
  }

  if (!analysis) {
    return (
      <form className="analysis-form" onSubmit={handleSubmit} noValidate>
        <h2>Create a new analysis</h2>

        <label>
          Course code
          <input value={courseCode} onChange={(e) => setCourseCode(e.target.value)} />
        </label>
        {errors.courseCode && <p className="field-error">{errors.courseCode}</p>}

        <label>
          Course name
          <input value={courseName} onChange={(e) => setCourseName(e.target.value)} />
        </label>
        {errors.courseName && <p className="field-error">{errors.courseName}</p>}

        <fieldset>
          <legend>Exam type</legend>
          {EXAM_TYPES.map((type) => (
            <label key={type} className="radio-option">
              <input
                type="radio"
                name="exam_type"
                value={type}
                checked={examType === type}
                onChange={() => setExamType(type)}
              />
              {type}
            </label>
          ))}
        </fieldset>
        {errors.examType && <p className="field-error">{errors.examType}</p>}

        <label>
          Term
          <input
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="e.g. 2026 Spring"
          />
        </label>
        {errors.term && <p className="field-error">{errors.term}</p>}

        {submitError && (
          <p className="field-error" role="alert">
            {submitError}
          </p>
        )}

        <button type="submit" disabled={isCreating}>
          {isCreating ? 'Creating…' : 'Create analysis'}
        </button>
      </form>
    )
  }

  return (
    <div className="analysis-upload">
      <h2>
        {analysis.course.code} — {analysis.exam_type} ({analysis.term})
      </h2>
      <p>
        Both the examination PDF and the populated TP-153 are required before this analysis can
        proceed.
      </p>

      <FileUploadField
        analysisId={analysis.id}
        fileType="exam"
        label="Examination PDF"
        uploaded={findUploaded('exam')}
        onUploaded={refreshAnalysis}
      />
      <FileUploadField
        analysisId={analysis.id}
        fileType="tp153"
        label="Populated TP-153"
        uploaded={findUploaded('tp153')}
        onUploaded={refreshAnalysis}
      />

      {analysis.ready_for_analysis ? (
        <div className="notice notice-success">
          <p>Both required documents are uploaded.</p>
          <ProcessingStatus
            analysisId={analysis.id}
            initialState={analysis.state}
            onStateChange={setProcessingState}
          />
        </div>
      ) : (
        <p className="notice">Upload both the examination PDF and the populated TP-153 to continue.</p>
      )}

      {(processingState ?? analysis.state) === 'completed' && (
        <AnalysisResults key={analysis.id} analysis={analysis} />
      )}
    </div>
  )
}
