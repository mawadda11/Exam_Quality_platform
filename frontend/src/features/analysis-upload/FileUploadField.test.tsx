import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { UploadedFileResponse } from '../../types/api'
import { FileUploadField } from './FileUploadField'

vi.mock('../../api/analyses')

const UPLOADED_EXAM: UploadedFileResponse = {
  id: 'file-1',
  file_type: 'exam',
  original_filename: 'exam.pdf',
  mime_type: 'application/pdf',
  size_bytes: 10,
  sha256_hash: 'a'.repeat(64),
  created_at: '2026-01-01T00:00:00Z',
}

function renderField(
  onUploaded: () => Promise<void> = vi.fn().mockResolvedValue(undefined),
) {
  return render(
    <FileUploadField
      analysisId="analysis-1"
      fileType="exam"
      label="Examination PDF"
      description="Select the examination PDF."
      contextLabel="Exam context"
      contextValue="Midterm — 2026 Spring"
      uploaded={undefined}
      onUploaded={onUploaded}
    />,
  )
}

function selectPdf(name = 'exam.pdf'): File {
  const file = new File(['%PDF-1.4'], name, { type: 'application/pdf' })
  fireEvent.change(screen.getByLabelText(/select examination pdf/i), {
    target: { files: [file] },
  })
  return file
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('FileUploadField', () => {
  it('moves from missing to selected without uploading automatically', () => {
    renderField()
    const input = screen.getByLabelText(/select examination pdf/i)

    expect(input.closest('section')).toHaveAttribute('data-upload-state', 'missing')
    selectPdf()

    expect(input.closest('section')).toHaveAttribute('data-upload-state', 'selected')
    expect(screen.getByText(/selected:/i)).toHaveTextContent('exam.pdf')
    expect(analysesApi.uploadAnalysisFile).not.toHaveBeenCalled()
  })

  it('rejects a non-PDF before calling the upload API', async () => {
    renderField()
    const file = new File(['not a pdf'], 'exam.txt', { type: 'text/plain' })

    fireEvent.change(screen.getByLabelText(/select examination pdf/i), {
      target: { files: [file] },
    })

    expect(await screen.findByText(/must be a PDF/i)).toBeInTheDocument()
    expect(screen.getByText('rejected')).toBeInTheDocument()
    expect(analysesApi.uploadAnalysisFile).not.toHaveBeenCalled()
  })

  it('shows uploading and then the backend-accepted upload', async () => {
    let resolveUpload: ((value: UploadedFileResponse) => void) | undefined
    vi.mocked(analysesApi.uploadAnalysisFile).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveUpload = resolve
        }),
    )
    const onUploaded = vi.fn().mockResolvedValue(undefined)
    renderField(onUploaded)
    const file = selectPdf()

    fireEvent.click(screen.getByRole('button', { name: /upload pdf/i }))
    await waitFor(() =>
      expect(screen.getByLabelText(/select examination pdf/i).closest('section'))
        .toHaveAttribute('data-upload-state', 'uploading'),
    )
    expect(screen.getByText('uploading')).toBeInTheDocument()

    resolveUpload?.(UPLOADED_EXAM)
    expect(await screen.findByText(/uploaded:/i)).toHaveTextContent('exam.pdf')
    expect(analysesApi.uploadAnalysisFile).toHaveBeenCalledWith(
      'analysis-1',
      'exam',
      file,
    )
    expect(onUploaded).toHaveBeenCalledTimes(1)
  })

  it('retains the selected file and retries only the rejected upload', async () => {
    vi.mocked(analysesApi.uploadAnalysisFile)
      .mockRejectedValueOnce(new ApiError(422, 'The PDF could not be read.'))
      .mockResolvedValueOnce(UPLOADED_EXAM)
    renderField()
    const file = selectPdf()

    fireEvent.click(screen.getByRole('button', { name: /upload pdf/i }))
    expect(await screen.findByText(/could not be read/i)).toBeInTheDocument()
    expect(screen.getByText('rejected')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /retry upload/i }))
    await waitFor(() =>
      expect(analysesApi.uploadAnalysisFile).toHaveBeenCalledTimes(2),
    )
    expect(analysesApi.uploadAnalysisFile).toHaveBeenLastCalledWith(
      'analysis-1',
      'exam',
      file,
    )
  })

  it('retries a failed authoritative refresh without uploading the file twice', async () => {
    vi.mocked(analysesApi.uploadAnalysisFile).mockResolvedValue(UPLOADED_EXAM)
    const onUploaded = vi
      .fn()
      .mockRejectedValueOnce(new ApiError(503, 'Could not refresh analysis.'))
      .mockResolvedValueOnce(undefined)
    renderField(onUploaded)
    selectPdf()

    fireEvent.click(screen.getByRole('button', { name: /upload pdf/i }))
    expect(await screen.findByText(/could not refresh analysis/i)).toBeInTheDocument()
    expect(screen.getByText(/has not yet confirmed readiness/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /retry status refresh/i }))
    await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(2))
    expect(analysesApi.uploadAnalysisFile).toHaveBeenCalledTimes(1)
  })
})
