import { useRef, useState, type FormEvent } from 'react'
import { createAnalysis } from '../../api/analyses'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import type { AnalysisResponse, ExamType, UploadedFileResponse } from '../../types/api'
import { FileUploadField } from './FileUploadField'
import { useI18n } from '../../i18n/I18nProvider'
import { localizeInterfaceError } from '../../i18n/localizeError'
import { validateAnalysisDetails, type AnalysisDetailsErrors } from './validation'

const EXAM_TYPES: ExamType[] = ['Midterm', 'Final']

interface AnalysisUploadFlowProps {
  onCreated: (analysis: AnalysisResponse) => void
}

export function AnalysisUploadFlow({ onCreated }: AnalysisUploadFlowProps) {
  const { locale, t } = useI18n()
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
        localizeInterfaceError(error, locale, t, 'Could not create analysis'),
      )
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <form className="analysis-form" onSubmit={handleSubmit} noValidate>
      <div>
        <h2>{t('Exam Information')}</h2>
        <p>{t('Enter the course and exam details. These details become read-only after creation.')}</p>
      </div>

      {Object.keys(errors).length > 0 && (
        <div
          ref={errorSummaryRef}
          className="analysis-error-summary"
          tabIndex={-1}
        >
          <Alert variant="error" title={t('Check the exam information')}>
            {t('Correct the highlighted fields and try again.')}
          </Alert>
        </div>
      )}

      <div className="analysis-form-field">
        <label htmlFor="course-code">{t('Course code')}</label>
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
        <label htmlFor="course-name">{t('Course name')}</label>
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
        <legend>{t('Exam type')}</legend>
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
              {t(type)}
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
        <label htmlFor="term">{t('Term')}</label>
        <input
          id="term"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          placeholder={t('e.g. 2026 Spring')}
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
        <Alert variant="error" title={t('Could not create analysis')}>
          {submitError}
        </Alert>
      )}

      <div className="analysis-form-actions">
        <Button type="submit" isLoading={isCreating} loadingLabel={t('Creating…')}>
          {t('Continue to Upload Documents')}
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
  const { t } = useI18n()
  function findUploaded(fileType: 'exam' | 'tp153'): UploadedFileResponse | undefined {
    return analysis.uploaded_files.find((file) => file.file_type === fileType)
  }

  return (
    <div className="analysis-upload">
      <div className="upload-cards">
        <FileUploadField
          analysisId={analysis.id}
          fileType="exam"
          label={t('Examination PDF')}
          description={t('Select the Midterm or Final examination PDF.')}
          contextLabel={t('Exam context')}
          contextValue={
            <>
              {t(analysis.exam_type)} — <bdi dir="auto">{analysis.term}</bdi>
            </>
          }
          uploaded={findUploaded('exam')}
          onUploaded={onRefreshed}
        />
        <FileUploadField
          analysisId={analysis.id}
          fileType="tp153"
          heading={t('Upload Course Specification')}
          label={t('Course Specification file')}
          description={t('Upload the completed official Course Specification PDF, such as a completed TP-153 template.')}
          contextLabel={t('Course context')}
          contextValue={
            <>
              <bdi>{analysis.course.code}</bdi> —{' '}
              <bdi dir="auto">{analysis.course.name}</bdi>
            </>
          }
          uploaded={findUploaded('tp153')}
          onUploaded={onRefreshed}
        />
      </div>

      {analysis.ready_for_analysis ? (
        <Alert variant="success" title={t('Documents ready')}>
          {t('The refreshed analysis confirms that both required documents are uploaded. Continue when you are ready to review and start.')}
        </Alert>
      ) : (
        <Alert variant="info" title={t('Both documents are required')}>
          {t('Both documents are required to continue. Unsaved file selections must be selected again after refreshing the page.')}
        </Alert>
      )}
    </div>
  )
}
