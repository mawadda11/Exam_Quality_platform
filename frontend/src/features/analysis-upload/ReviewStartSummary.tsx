import { Alert } from '../../components/ui/Alert'
import type { AnalysisResponse, UploadedFileResponse, UploadedFileType } from '../../types/api'

interface ReviewStartSummaryProps {
  analysis: AnalysisResponse
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
          'Not uploaded'
        )}
      </dd>
    </div>
  )
}

export function ReviewStartSummary({ analysis }: ReviewStartSummaryProps) {
  const exam = findFile(analysis, 'exam')
  const tp153 = findFile(analysis, 'tp153')

  return (
    <div className="review-start-summary">
      <div>
        <h2>Review and Start</h2>
        <p>Confirm the persisted details and uploaded documents before starting the analysis.</p>
      </div>

      <dl className="review-metadata">
        <div>
          <dt>Course code</dt>
          <dd>
            <bdi>{analysis.course.code}</bdi>
          </dd>
        </div>
        <div>
          <dt>Course name</dt>
          <dd>
            <bdi dir="auto">{analysis.course.name}</bdi>
          </dd>
        </div>
        <div>
          <dt>Exam type</dt>
          <dd>{analysis.exam_type}</dd>
        </div>
        <div>
          <dt>Term</dt>
          <dd>
            <bdi dir="auto">{analysis.term}</bdi>
          </dd>
        </div>
      </dl>

      <dl className="review-files">
        <FileSummary label="Examination PDF" file={exam} />
        <FileSummary label="Populated TP-153" file={tp153} />
      </dl>

      <Alert variant="info" title="Scope reminder">
        The analysis applies only to this uploaded examination and its corresponding populated
        TP-153. Starting the analysis does not issue an accreditation or institutional decision.
      </Alert>
    </div>
  )
}
