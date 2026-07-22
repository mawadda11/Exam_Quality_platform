import { useState, type ChangeEvent } from 'react'
import { uploadAnalysisFile } from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { UploadedFileResponse, UploadedFileType } from '../../types/api'
import { isPdfFile } from './validation'

interface FileUploadFieldProps {
  analysisId: string
  fileType: UploadedFileType
  label: string
  uploaded: UploadedFileResponse | undefined
  onUploaded: () => void | Promise<void>
}

export function FileUploadField({
  analysisId,
  fileType,
  label,
  uploaded,
  onUploaded,
}: FileUploadFieldProps) {
  const [error, setError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)

  async function handleChange(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    if (!isPdfFile(file)) {
      setError(`"${file.name}" must be a .pdf file.`)
      return
    }

    setError(null)
    setIsUploading(true)
    try {
      await uploadAnalysisFile(analysisId, fileType, file)
      await onUploaded()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Upload failed. Please try again.')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="file-field">
      <label>
        <span className="file-field-label">{label} (required)</span>
        <input
          type="file"
          accept="application/pdf,.pdf"
          disabled={isUploading || Boolean(uploaded)}
          onChange={handleChange}
          aria-label={label}
        />
      </label>
      {isUploading && <p className="file-field-status">Uploading…</p>}
      {uploaded && (
        <p className="file-field-status file-field-status-success">
          Uploaded: {uploaded.original_filename}
        </p>
      )}
      {error && (
        <p className="file-field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
