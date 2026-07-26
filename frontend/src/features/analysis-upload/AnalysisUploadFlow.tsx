import { useState, type FormEvent } from 'react'
import { createAnalysis } from '../../api/analyses'
import { ApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import type { AnalysisResponse, ExamType, UploadedFileResponse } from '../../types/api'
import { FileUploadField } from './FileUploadField'
import { validateAnalysisDetails, type AnalysisDetailsErrors } from './validation'

const EXAM_TYPES: ExamType[] = ['Midterm', 'Final']

interface AnalysisUploadFlowProps {
  onCreated: (analysis: AnalysisResponse) => void
}

export function AnalysisUploadFlow({ onCreated }: AnalysisUploadFlowProps) {
  const [courseCode, setCourseCode] = useState('')
  const [courseName, setCourseName] = useState('')
  const [examType, setExamType] = useState<ExamType | ''>('')
  const [term, setTerm] = useState('')
  const [errors, setErrors] = useState<AnalysisDetailsErrors>({})
  const [isCreating, setIsCreating] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

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
      onCreated(created)
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.detail : 'Could not create the analysis.')
    } finally {
      setIsCreating(false)
    }
  }

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
        <Alert variant="error" title="Could not create analysis">
          {submitError}
        </Alert>
      )}

      <Button type="submit" isLoading={isCreating} loadingLabel="Creating…">
        Create analysis
      </Button>
    </form>
  )
}

interface AnalysisDocumentsProps {
  analysis: AnalysisResponse
  onRefreshed: () => Promise<void>
}

export function AnalysisDocuments({ analysis, onRefreshed }: AnalysisDocumentsProps) {
  function findUploaded(fileType: 'exam' | 'tp153'): UploadedFileResponse | undefined {
    return analysis.uploaded_files.find((file) => file.file_type === fileType)
  }

  return (
    <div className="analysis-upload">
      <h2>
        <bdi>{analysis.course.code}</bdi> — {analysis.exam_type} ({analysis.term})
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
        onUploaded={onRefreshed}
      />
      <FileUploadField
        analysisId={analysis.id}
        fileType="tp153"
        label="Populated TP-153"
        uploaded={findUploaded('tp153')}
        onUploaded={onRefreshed}
      />

      {analysis.ready_for_analysis ? (
        <p className="notice notice-success">Both required documents are uploaded.</p>
      ) : (
        <p className="notice">Upload both the examination PDF and the populated TP-153 to continue.</p>
      )}
    </div>
  )
}
