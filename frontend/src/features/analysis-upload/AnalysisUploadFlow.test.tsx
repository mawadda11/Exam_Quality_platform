import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as analysesApi from '../../api/analyses'
import { ApiError } from '../../api/client'
import type { AnalysisResponse, UploadedFileResponse } from '../../types/api'
import { AnalysisDocuments, AnalysisUploadFlow } from './AnalysisUploadFlow'

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
  vi.clearAllMocks()
})

function fillCreateForm(): void {
  fireEvent.change(screen.getByLabelText(/course code/i), {
    target: { value: 'CPIT-450' },
  })
  fireEvent.change(screen.getByLabelText(/course name/i), {
    target: { value: 'Software Engineering' },
  })
  fireEvent.click(screen.getByRole('radio', { name: 'Midterm' }))
  fireEvent.change(screen.getByLabelText(/^term$/i), {
    target: { value: '2026 Spring' },
  })
}

describe('AnalysisUploadFlow', () => {
  it('focuses the validation summary and does not call the API when required fields are empty', async () => {
    render(<AnalysisUploadFlow onCreated={vi.fn()} />)

    fireEvent.click(
      screen.getByRole('button', { name: /continue to upload documents/i }),
    )

    const summary = await screen.findByText(/correct the highlighted fields/i)
    await waitFor(() => expect(summary.closest('[tabindex="-1"]')).toHaveFocus())
    expect(screen.getByLabelText(/course code/i)).toHaveAttribute('aria-invalid', 'true')
    expect(analysesApi.createAnalysis).not.toHaveBeenCalled()
  })

  it('creates the analysis with the existing payload and reports it to the route adapter', async () => {
    const onCreated = vi.fn()
    vi.mocked(analysesApi.createAnalysis).mockResolvedValue(BASE_ANALYSIS)
    render(<AnalysisUploadFlow onCreated={onCreated} />)
    fillCreateForm()

    fireEvent.click(
      screen.getByRole('button', { name: /continue to upload documents/i }),
    )

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(BASE_ANALYSIS))
    expect(analysesApi.createAnalysis).toHaveBeenCalledWith({
      course: { code: 'CPIT-450', name: 'Software Engineering' },
      exam_type: 'Midterm',
      term: '2026 Spring',
    })
  })

  it('shows persisted metadata and browser refresh limitations on the documents step', () => {
    render(<AnalysisDocuments analysis={BASE_ANALYSIS} onRefreshed={vi.fn()} />)

    expect(screen.getByText('CPIT-450')).toBeInTheDocument()
    expect(screen.getByText(/software engineering/i)).toBeInTheDocument()
    expect(screen.getByText(/browser will require you to select that file again/i))
      .toBeInTheDocument()
    expect(
      screen.getByText( /arabic, english, and mixed examination and tp-153 pdf files are supported/i),
    ).toBeInTheDocument()
    expect(screen.getAllByText('missing')).toHaveLength(2)
  })

  it('renders only backend-confirmed readiness and persisted uploaded files', () => {
    const readyAnalysis: AnalysisResponse = {
      ...BASE_ANALYSIS,
      uploaded_files: [UPLOADED_EXAM, UPLOADED_TP153],
      exam_uploaded: true,
      tp153_uploaded: true,
      ready_for_analysis: true,
    }

    render(<AnalysisDocuments analysis={readyAnalysis} onRefreshed={vi.fn()} />)

    expect(screen.getByText(/refreshed analysis confirms/i)).toBeInTheDocument()
    expect(screen.getByText(/exam\.pdf/i)).toBeInTheDocument()
    expect(screen.getByText(/tp153\.pdf/i)).toBeInTheDocument()
    expect(analysesApi.uploadAnalysisFile).not.toHaveBeenCalled()
  })

  it('shows a create-analysis API error and keeps the information form available', async () => {
    vi.mocked(analysesApi.createAnalysis).mockRejectedValueOnce(
      new ApiError(422, "['term': field required]"),
    )
    render(<AnalysisUploadFlow onCreated={vi.fn()} />)
    fillCreateForm()

    fireEvent.click(
      screen.getByRole('button', { name: /continue to upload documents/i }),
    )

    expect(await screen.findByText(/field required/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /continue to upload documents/i }),
    ).toBeInTheDocument()
  })
})
