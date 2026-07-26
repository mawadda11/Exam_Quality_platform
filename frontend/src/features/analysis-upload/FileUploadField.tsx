import { useId, useState, type ChangeEvent } from 'react'
import { uploadAnalysisFile } from '../../api/analyses'
import { ApiError } from '../../api/client'
import { Button } from '../../components/ui/Button'
import type { UploadedFileResponse, UploadedFileType } from '../../types/api'
import { isPdfFile } from './validation'

interface FileUploadFieldProps {
  analysisId: string
  fileType: UploadedFileType
  label: string
  description: string
  uploaded: UploadedFileResponse | undefined
  onUploaded: () => Promise<void>
}

export function FileUploadField({
  analysisId,
  fileType,
  label,
  description,
  uploaded,
  onUploaded,
}: FileUploadFieldProps) {
  const inputId = useId()
  const descriptionId = `${inputId}-description`
  const statusId = `${inputId}-status`
  const errorId = `${inputId}-error`
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [acceptedUpload, setAcceptedUpload] = useState<UploadedFileResponse | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  function handleChange(event: ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    setAcceptedUpload(null)
    setRefreshError(null)
    if (!isPdfFile(file)) {
      setSelectedFile(null)
      setUploadError(`"${file.name}" must be a .pdf file.`)
      return
    }

    setSelectedFile(file)
    setUploadError(null)
  }

  async function refreshAuthoritativeState(): Promise<void> {
    setIsRefreshing(true)
    setRefreshError(null)
    try {
      await onUploaded()
    } catch (error) {
      setRefreshError(
        error instanceof ApiError
          ? error.detail
          : 'The upload was accepted, but the analysis status could not be refreshed.',
      )
    } finally {
      setIsRefreshing(false)
    }
  }

  async function handleUpload(): Promise<void> {
    if (!selectedFile) return

    setIsUploading(true)
    setUploadError(null)
    setRefreshError(null)
    try {
      const response = await uploadAnalysisFile(analysisId, fileType, selectedFile)
      setAcceptedUpload(response)
      await refreshAuthoritativeState()
    } catch (error) {
      setUploadError(
        error instanceof ApiError ? error.detail : 'Upload failed. Please try again.',
      )
    } finally {
      setIsUploading(false)
    }
  }

  const displayedUpload = uploaded ?? acceptedUpload
  const isAwaitingRefresh = Boolean(acceptedUpload && !uploaded)
  const state = displayedUpload
    ? 'uploaded'
    : uploadError
      ? 'rejected'
      : isUploading
        ? 'uploading'
        : selectedFile
          ? 'selected'
          : 'missing'
  const describedBy = [descriptionId, statusId, uploadError ? errorId : null]
    .filter(Boolean)
    .join(' ')

  return (
    <section className="file-upload-card" data-upload-state={state}>
      <div className="file-upload-heading">
        <div>
          <h3 id={`${inputId}-label`}>{label}</h3>
          <p id={descriptionId}>{description}</p>
        </div>
        <span className="file-upload-state">{state}</span>
      </div>

      <label className="visually-hidden" htmlFor={inputId}>
        Select {label}
      </label>
      <input
        id={inputId}
        className="file-upload-input"
        type="file"
        accept="application/pdf,.pdf"
        disabled={isUploading || isRefreshing || Boolean(displayedUpload)}
        onChange={handleChange}
        aria-describedby={describedBy}
      />

      <div id={statusId} className="file-upload-status" aria-live="polite">
        {!displayedUpload && !selectedFile && !uploadError && 'No PDF selected.'}
        {selectedFile && !isUploading && !displayedUpload && (
          <>
            Selected: <bdi dir="auto">{selectedFile.name}</bdi>
          </>
        )}
        {isUploading && (
          <>
            Uploading <bdi dir="auto">{selectedFile?.name}</bdi>…
          </>
        )}
        {displayedUpload && (
          <span className="file-upload-status--success">
            Uploaded: <bdi dir="auto">{displayedUpload.original_filename}</bdi>
          </span>
        )}
      </div>

      {isAwaitingRefresh && (
        <p className="file-upload-status">
          The upload response was received. The refreshed analysis has not yet confirmed readiness.
        </p>
      )}
      {!uploaded && uploadError && (
        <p id={errorId} className="file-upload-status file-upload-status--error" role="alert">
          {uploadError}
        </p>
      )}
      {!uploaded && refreshError && (
        <p className="file-upload-status file-upload-status--error" role="alert">
          {refreshError}
        </p>
      )}

      <div className="file-upload-actions">
        {!displayedUpload && selectedFile && (
          <Button
            onClick={() => void handleUpload()}
            isLoading={isUploading}
            loadingLabel="Uploading…"
          >
            {uploadError ? 'Retry upload' : 'Upload PDF'}
          </Button>
        )}
        {isAwaitingRefresh && (
          <Button
            variant="secondary"
            onClick={() => void refreshAuthoritativeState()}
            isLoading={isRefreshing}
            loadingLabel="Refreshing…"
          >
            Retry status refresh
          </Button>
        )}
      </div>
    </section>
  )
}
