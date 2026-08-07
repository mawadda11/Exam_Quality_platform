import { Alert } from '../../components/ui/Alert'
import { useI18n } from '../../i18n/I18nProvider'
import type {
  AnalysisResponse,
  QuestionPreparationMode,
  UploadedFileResponse,
  UploadedFileType,
} from '../../types/api'

interface ReviewStartSummaryProps {
  analysis: AnalysisResponse
  questionPreparationMode: QuestionPreparationMode
  onQuestionPreparationModeChange: (mode: QuestionPreparationMode) => void
}

function findFile(
  analysis: AnalysisResponse,
  fileType: UploadedFileType,
): UploadedFileResponse | undefined {
  return analysis.uploaded_files.find((file) => file.file_type === fileType)
}

function formatFileSize(sizeBytes: number): string {
  if (sizeBytes < 1024) return `${sizeBytes} bytes`
  return `${(sizeBytes / 1024).toFixed(1)} KB`
}

function FileSummary({
  label,
  file,
}: {
  label: string
  file: UploadedFileResponse | undefined
}) {
  const { t } = useI18n()
  return (
    <div className="review-file">
      <dt>{label}</dt>
      <dd>
        {file ? (
          <>
            <bdi dir="auto">{file.original_filename}</bdi>
            <span>{formatFileSize(file.size_bytes)}</span>
          </>
        ) : (
          t('Not uploaded')
        )}
      </dd>
    </div>
  )
}

export function ReviewStartSummary({
  analysis,
  questionPreparationMode,
  onQuestionPreparationModeChange,
}: ReviewStartSummaryProps) {
  const { t } = useI18n()
  const exam = findFile(analysis, 'exam')
  const tp153 = findFile(analysis, 'tp153')

  return (
    <div className="review-start-summary">
      <div>
        <h2>{t('Review and Start')}</h2>
        <p>{t('Confirm the persisted details and uploaded documents before starting the analysis.')}</p>
      </div>

      <dl className="review-metadata">
        <div>
          <dt>{t('Course code')}</dt>
          <dd>
            <bdi>{analysis.course.code}</bdi>
          </dd>
        </div>
        <div>
          <dt>{t('Course name')}</dt>
          <dd>
            <bdi dir="auto">{analysis.course.name}</bdi>
          </dd>
        </div>
        <div>
          <dt>{t('Exam type')}</dt>
          <dd>{t(analysis.exam_type)}</dd>
        </div>
        <div>
          <dt>{t('Term')}</dt>
          <dd>
            <bdi dir="auto">{analysis.term}</bdi>
          </dd>
        </div>
      </dl>

      <dl className="review-files">
        <FileSummary label={t('Examination PDF')} file={exam} />
        <FileSummary label={t('Course Specification file')} file={tp153} />
      </dl>

      <fieldset className="question-preparation-fieldset">
        <legend>{t('How should questions be prepared?')}</legend>
        <p>{t('Choose the safest workflow for the uploaded exam. The academic analysis starts only after you confirm the questions.')}</p>
        <div className="question-preparation-options">
          <label className="question-preparation-option">
            <input
              type="radio"
              name="question-preparation-mode"
              value="assisted_pdf"
              checked={questionPreparationMode === 'assisted_pdf'}
              onChange={() => onQuestionPreparationModeChange('assisted_pdf')}
            />
            <span>
              <strong>{t('Assisted extraction from PDF')}</strong>
              <small>{t('Best for clear digital exams. The platform proposes questions and you correct only the items that need attention.')}</small>
              <b>{t('Recommended starting point')}</b>
            </span>
          </label>
          <label className="question-preparation-option">
            <input
              type="radio"
              name="question-preparation-mode"
              value="structured_template"
              checked={questionPreparationMode === 'structured_template'}
              onChange={() => onQuestionPreparationModeChange('structured_template')}
            />
            <span>
              <strong>{t('Paste or import question list')}</strong>
              <small>{t('Paste questions copied from Word or import a simple CSV. Only number, text, and visible marks are required.')}</small>
            </span>
          </label>
        </div>
        <p className="question-preparation-fallback-note">
          {t('Missing questions can still be added from the PDF inside the review screen.')}
        </p>
      </fieldset>

      <Alert variant="info" title={t('Scope reminder')}>
        {t('The analysis applies only to this uploaded examination and its corresponding Course Specification. Starting the analysis does not issue an accreditation or institutional decision.')}
      </Alert>
    </div>
  )
}
