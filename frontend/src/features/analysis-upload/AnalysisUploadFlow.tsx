import { useRef, useState, type FormEvent } from 'react'
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
  const errorSummaryRef = useRef<HTMLDivElement>(null)
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
    if (Object.keys(validationErrors).length > 0) {
      requestAnimationFrame(() => errorSummaryRef.current?.focus())
      return
    }

    setIsCreating(true)
    setSubmitError(null)
    try {
      const created = await createAnalysis({
        course: { code: courseCode, name: courseName },
        exam_type: examType as ExamType,
        term,
      })
      onCreated(created)
    } catch (error) {
      setSubmitError(
        error instanceof ApiError ? error.detail : 'Could not create the analysis.',
      )
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <form className="analysis-form" onSubmit={handleSubmit} noValidate>
      <div>
        <h2>Exam Information</h2>
        <p>Enter the course and exam details. These details become read-only after creation.</p>
      </div>

      {Object.keys(errors).length > 0 && (
        <div
          ref={errorSummaryRef}
          className="analysis-error-summary"
          tabIndex={-1}
        >
          <Alert variant="error" title="Check the exam information">
            Correct the highlighted fields and try again.
          </Alert>
        </div>
      )}

      <div className="analysis-form-field">
        <label htmlFor="course-code">Course code</label>
        <input
          id="course-code"
          value={courseCode}
          onChange={(event) => setCourseCode(event.target.value)}
          aria-invalid={Boolean(errors.courseCode)}
          aria-describedby={errors.courseCode ? 'course-code-error' : undefined}
        />
        {errors.courseCode && (
          <p id="course-code-error" className="field-error">
            {errors.courseCode}
          </p>
        )}
      </div>

      <div className="analysis-form-field">
        <label htmlFor="course-name">Course name</label>
        <input
          id="course-name"
          value={courseName}
          onChange={(event) => setCourseName(event.target.value)}
          aria-invalid={Boolean(errors.courseName)}
          aria-describedby={errors.courseName ? 'course-name-error' : undefined}
        />
        {errors.courseName && (
          <p id="course-name-error" className="field-error">
            {errors.courseName}
          </p>
        )}
      </div>

      <fieldset
        aria-invalid={Boolean(errors.examType)}
        aria-describedby={errors.examType ? 'exam-type-error' : undefined}
      >
        <legend>Exam type</legend>
        <div className="analysis-form-options">
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
        </div>
      </fieldset>
      {errors.examType && (
        <p id="exam-type-error" className="field-error">
          {errors.examType}
        </p>
      )}

      <div className="analysis-form-field">
        <label htmlFor="term">Term</label>
        <input
          id="term"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          placeholder="e.g. 2026 Spring"
          aria-invalid={Boolean(errors.term)}
          aria-describedby={errors.term ? 'term-error' : undefined}
        />
        {errors.term && (
          <p id="term-error" className="field-error">
            {errors.term}
          </p>
        )}
      </div>

      {submitError && (
        <Alert variant="error" title="Could not create analysis">
          {submitError}
        </Alert>
      )}

      <div className="analysis-form-actions">
        <Button type="submit" isLoading={isCreating} loadingLabel="Creating…">
          Continue to Upload Documents
        </Button>
      </div>
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
      <div>
        <h2>Upload Documents</h2>
        <p>
          Both the examination PDF and the populated TP-153 are required. Each upload can be
          retried independently.
        </p>
        <p className="results-supporting-text">
          English-language examination and TP-153 PDF files are supported.
        </p>
      </div>

      <dl className="analysis-persisted-summary" aria-label="Persisted exam information">
        <div>
          <dt>Course</dt>
          <dd>
            <bdi>{analysis.course.code}</bdi> —{' '}
            <bdi dir="auto">{analysis.course.name}</bdi>
          </dd>
        </div>
        <div>
          <dt>Exam</dt>
          <dd>
            {analysis.exam_type} — <bdi dir="auto">{analysis.term}</bdi>
          </dd>
        </div>
      </dl>

      <div className="upload-cards">
        <FileUploadField
          analysisId={analysis.id}
          fileType="exam"
          label="Examination PDF"
          description="Select the Midterm or Final examination PDF."
          uploaded={findUploaded('exam')}
          onUploaded={onRefreshed}
        />
        <FileUploadField
          analysisId={analysis.id}
          fileType="tp153"
          label="Populated TP-153"
          description="Select the populated course specification PDF."
          uploaded={findUploaded('tp153')}
          onUploaded={onRefreshed}
        />
      </div>

      {analysis.ready_for_analysis ? (
        <Alert variant="success" title="Documents ready">
          The refreshed analysis confirms that both required documents are uploaded. Continue when
          you are ready to review and start.
        </Alert>
      ) : (
        <Alert variant="info" title="Both documents are required">
          Upload both PDFs to continue. If this page is refreshed before a selected file is
          uploaded, the browser will require you to select that file again.
        </Alert>
      )}
    </div>
  )
}
