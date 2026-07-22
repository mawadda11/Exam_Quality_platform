import { afterEach, describe, expect, it, vi } from 'vitest'
import { createAnalysis, getAnalysis, uploadAnalysisFile } from './analyses'
import type { AnalysisResponse, UploadedFileResponse } from '../types/api'

function mockResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: '',
    json: async () => body,
  } as unknown as Response
}

const SAMPLE_ANALYSIS: AnalysisResponse = {
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
  uploaded_files: [],
  exam_uploaded: false,
  tp153_uploaded: false,
  ready_for_analysis: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('createAnalysis', () => {
  it('POSTs to /analyses with the given payload and returns the created analysis', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(SAMPLE_ANALYSIS, 201))
    vi.stubGlobal('fetch', fetchMock)

    const result = await createAnalysis({
      course: { code: 'CPIT-450', name: 'Software Engineering' },
      exam_type: 'Midterm',
      term: '2026 Spring',
    })

    expect(result).toEqual(SAMPLE_ANALYSIS)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/api/v1/analyses')
    expect(init.method).toBe('POST')
  })
})

describe('getAnalysis', () => {
  it('GETs /analyses/{id}', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(SAMPLE_ANALYSIS))
    vi.stubGlobal('fetch', fetchMock)

    const result = await getAnalysis('analysis-1')

    expect(result.id).toBe('analysis-1')
    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/api/v1/analyses/analysis-1')
  })
})

describe('uploadAnalysisFile', () => {
  it('POSTs multipart form data containing file_type and the file', async () => {
    const uploadedFile: UploadedFileResponse = {
      id: 'file-1',
      file_type: 'exam',
      original_filename: 'exam.pdf',
      mime_type: 'application/pdf',
      size_bytes: 3,
      sha256_hash: 'a'.repeat(64),
      created_at: '2026-01-01T00:00:00Z',
    }
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(uploadedFile, 201))
    vi.stubGlobal('fetch', fetchMock)

    const file = new File([new Uint8Array([1, 2, 3])], 'exam.pdf', { type: 'application/pdf' })
    const result = await uploadAnalysisFile('analysis-1', 'exam', file)

    expect(result.file_type).toBe('exam')
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('http://localhost:8000/api/v1/analyses/analysis-1/files')
    expect(init.method).toBe('POST')
    const form = init.body as FormData
    expect(form.get('file_type')).toBe('exam')
    expect((form.get('file') as File).name).toBe('exam.pdf')
  })
})
