import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse, UploadedFileResponse } from '../../types/api'
import { AnalysisUploadFlow } from './AnalysisUploadFlow'

vi.mock('../../api/analyses')

const BASE_ANALYSIS: AnalysisResponse = {
  id: 'analysis-1',
  course: {
    id: 'course-1',
    code: 'CPIT-450',
    name: 'Software Engineering',
    department: null,
    program: null,
  },
  exam_type: 'Midterm',
  term: '2026 Spring',
  state: 'queued',
  owner_user_id: 'user-1',
  predecessor_analysis_id: null,
  uploaded_files: [],
  exam_uploaded: false,
  tp153_uploaded: false,
  ready_for_analysis: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const UPLOADED_EXAM: UploadedFileResponse = {
  id: 'file-1',
  file_type: 'exam',
  original_filename: 'exam.pdf',
  mime_type: 'application/pdf',
  size_bytes: 10,
  sha256_hash: 'a'.repeat(64),
  created_at: '2026-01-01T00:00:00Z',
}

const UPLOADED_TP153: UploadedFileResponse = {
  id: 'file-2',
  file_type: 'tp153',
  original_filename: 'tp153.pdf',
  mime_type: 'application/pdf',
  size_bytes: 10,
  sha256_hash: 'b'.repeat(64),
  created_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.mocked(analysesApi.createAnalysis).mockReset()
  vi.mocked(analysesApi.getAnalysis).mockReset()
  vi.mocked(analysesApi.uploadAnalysisFile).mockReset()
  // The history list fetches on mount whenever no analysis is selected yet -
  // default to empty so existing tests (which don't care about history)
  // don't need to know about it.
  vi.mocked(analysesApi.listAnalyses).mockReset().mockResolvedValue([])
})

function fillCreateForm(): void {
  fireEvent.change(screen.getByLabelText(/course code/i), { target: { value: 'CPIT-450' } })
  fireEvent.change(screen.getByLabelText(/course name/i), {
    target: { value: 'Software Engineering' },
  })
  fireEvent.click(screen.getByRole('radio', { name: 'Midterm' }))
  fireEvent.change(screen.getByLabelText(/^term$/i), { target: { value: '2026 Spring' } })
}

async function createValidAnalysis(): Promise<void> {
  vi.mocked(analysesApi.createAnalysis).mockResolvedValue(BASE_ANALYSIS)
  render(<AnalysisUploadFlow />)
  fillCreateForm()
  fireEvent.click(screen.getByRole('button', { name: /create analysis/i }))
  await screen.findByLabelText(/examination pdf/i)
}

describe('AnalysisUploadFlow', () => {
  it('shows validation errors and does not call the API when required fields are empty', async () => {
    render(<AnalysisUploadFlow />)

    fireEvent.click(screen.getByRole('button', { name: /create analysis/i }))

    expect(await screen.findByText(/course code is required/i)).toBeInTheDocument()
    expect(analysesApi.createAnalysis).not.toHaveBeenCalled()
  })

  it('creates the analysis and shows both required file inputs, with no mode selector', async () => {
    await createValidAnalysis()

    expect(screen.getByLabelText(/examination pdf/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/populated tp-153/i)).toBeInTheDocument()
    expect(screen.queryByText(/analysis mode/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/limited exam review/i)).not.toBeInTheDocument()
  })

  it('rejects a non-pdf file client-side without calling the upload API', async () => {
    await createValidAnalysis()

    const examInput = screen.getByLabelText(/examination pdf/i)
    const badFile = new File(['not a pdf'], 'exam.txt', { type: 'text/plain' })
    fireEvent.change(examInput, { target: { files: [badFile] } })

    expect(await screen.findByText(/must be a \.pdf file/i)).toBeInTheDocument()
    expect(analysesApi.uploadAnalysisFile).not.toHaveBeenCalled()
  })

  it('uploads a valid pdf and reflects ready_for_analysis once both files are present', async () => {
    await createValidAnalysis()
    vi.mocked(analysesApi.uploadAnalysisFile).mockResolvedValueOnce(UPLOADED_EXAM)
    vi.mocked(analysesApi.getAnalysis).mockResolvedValueOnce({
      ...BASE_ANALYSIS,
      exam_uploaded: true,
      uploaded_files: [UPLOADED_EXAM],
    })

    const examInput = screen.getByLabelText(/examination pdf/i)
    const goodFile = new File(['%PDF-1.4'], 'exam.pdf', { type: 'application/pdf' })
    fireEvent.change(examInput, { target: { files: [goodFile] } })

    await waitFor(() =>
      expect(analysesApi.uploadAnalysisFile).toHaveBeenCalledWith('analysis-1', 'exam', goodFile),
    )
    expect(await screen.findByText(/uploaded: exam\.pdf/i)).toBeInTheDocument()
    expect(screen.getByText(/upload both the examination pdf/i)).toBeInTheDocument()

    vi.mocked(analysesApi.uploadAnalysisFile).mockResolvedValueOnce(UPLOADED_TP153)
    vi.mocked(analysesApi.getAnalysis).mockResolvedValueOnce({
      ...BASE_ANALYSIS,
      exam_uploaded: true,
      tp153_uploaded: true,
      ready_for_analysis: true,
      uploaded_files: [UPLOADED_EXAM, UPLOADED_TP153],
    })

    const tp153Input = screen.getByLabelText(/populated tp-153/i)
    const tp153File = new File(['%PDF-1.4'], 'tp153.pdf', { type: 'application/pdf' })
    fireEvent.change(tp153Input, { target: { files: [tp153File] } })

    expect(await screen.findByText(/both required documents are uploaded/i)).toBeInTheDocument()
  })

  it('surfaces a server error message without marking the file as uploaded', async () => {
    await createValidAnalysis()
    vi.mocked(analysesApi.uploadAnalysisFile).mockRejectedValueOnce(
      new ApiError(409, 'A exam file has already been uploaded for this analysis.'),
    )

    const examInput = screen.getByLabelText(/examination pdf/i)
    const goodFile = new File(['%PDF-1.4'], 'exam.pdf', { type: 'application/pdf' })
    fireEvent.change(examInput, { target: { files: [goodFile] } })

    expect(await screen.findByText(/already been uploaded/i)).toBeInTheDocument()
    expect(screen.queryByText(/uploaded: exam\.pdf/i)).not.toBeInTheDocument()
  })

  it('shows a create-analysis error and stays on the form when the API call fails', async () => {
    vi.mocked(analysesApi.createAnalysis).mockRejectedValueOnce(
      new ApiError(422, "['term': field required]"),
    )
    render(<AnalysisUploadFlow />)
    fillCreateForm()

    fireEvent.click(screen.getByRole('button', { name: /create analysis/i }))

    expect(await screen.findByText(/field required/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create analysis/i })).toBeInTheDocument()
  })

  it('does not show a history list when the user has no prior analyses', async () => {
    render(<AnalysisUploadFlow />)
    await waitFor(() => expect(analysesApi.listAnalyses).toHaveBeenCalled())
    expect(screen.queryByText(/your analyses/i)).not.toBeInTheDocument()
  })

  it('shows a history list and loads the selected analysis directly, skipping the create form', async () => {
    vi.mocked(analysesApi.listAnalyses).mockResolvedValue([BASE_ANALYSIS])

    render(<AnalysisUploadFlow />)

    expect(await screen.findByText(/your analyses/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /CPIT-450.*Midterm/ }))

    expect(await screen.findByLabelText(/examination pdf/i)).toBeInTheDocument()
    expect(analysesApi.createAnalysis).not.toHaveBeenCalled()
  })
})
