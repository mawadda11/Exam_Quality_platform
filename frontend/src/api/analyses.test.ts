import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  confirmExtractionReview,
  createAnalysis,
  getAnalysis,
  getExtractionReview,
  listFindings,
  parseFindingResponses,
  saveExtractionReview,
  uploadAnalysisFile,
} from './analyses'
import type {
  AnalysisResponse,
  ExtractionReviewConfirmResponse,
  ExtractionReviewResponse,
  ExtractionReviewSnapshot,
  FindingResponse,
  UploadedFileResponse,
} from '../types/api'

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
  predecessor_analysis_id: null,
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

const SEMANTIC_FINDING: FindingResponse = {
  id: 'finding-1',
  analysis_id: 'analysis-1',
  requirement_id: 'REQ002',
  rule_id: 'RULE002',
  recommendation_id: null,
  status: 'Satisfied',
  explanation: 'The question is relevant to the mapped CLO.',
  confidence: 0.84,
  evaluator_type: 'semantic_ai',
  ai_provider: 'fake',
  ai_model: 'fake-semantic-v1',
  prompt_template_version: 'semantic-rule002-v1',
  kb_version: '1.0.0',
  created_at: '2026-01-01T00:00:00Z',
  evidence: [],
  requirement_name: 'CLO Relevance',
  dimension: 'CLO Alignment',
  source_type: 'Derived Exam Requirement',
  officiality: 'Derived',
}

describe('listFindings', () => {
  it('accepts the expanded semantic provenance payload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(mockResponse([SEMANTIC_FINDING])))
    const result = await listFindings('analysis-1')
    expect(result).toEqual([SEMANTIC_FINDING])
  })

  it('rejects a malformed finding response at the API boundary', () => {
    const malformed = { ...SEMANTIC_FINDING }
    delete (malformed as Partial<FindingResponse>).prompt_template_version
    expect(() => parseFindingResponses([malformed])).toThrow(/malformed findings response/i)
  })
})

const REVIEW_SNAPSHOT: ExtractionReviewSnapshot = {
  schema_version: 1,
  questions: [],
  evidence: [],
  clos: [],
  topics: [],
  assessment_records: [],
}

const REVIEW_RESPONSE: ExtractionReviewResponse = {
  analysis_id: 'analysis-1',
  revision_id: 'revision-1',
  revision_number: 1,
  created_at: '2026-07-26T00:00:00Z',
  snapshot: REVIEW_SNAPSHOT,
  original_snapshot: REVIEW_SNAPSHOT,
  confirmed_revision_id: null,
  is_confirmed: false,
  can_edit: true,
  can_confirm: true,
  warnings: [],
  confirmation_blockers: [],
}

describe('extraction review API', () => {
  it('loads the latest review revision with GET', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(REVIEW_RESPONSE))
    vi.stubGlobal('fetch', fetchMock)

    expect(await getExtractionReview('analysis-1')).toEqual(REVIEW_RESPONSE)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(
      'http://localhost:8000/api/v1/analyses/analysis-1/extraction-review',
    )
    expect(init.method).toBeUndefined()
  })

  it('saves a complete source-faithful snapshot with PUT', async () => {
    const saved = { ...REVIEW_RESPONSE, revision_id: 'revision-2', revision_number: 2 }
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(saved, 201))
    vi.stubGlobal('fetch', fetchMock)

    expect(
      await saveExtractionReview('analysis-1', 'revision-1', REVIEW_SNAPSHOT),
    ).toEqual(saved)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(
      'http://localhost:8000/api/v1/analyses/analysis-1/extraction-review',
    )
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body as string)).toEqual({
      base_revision_id: 'revision-1',
      snapshot: REVIEW_SNAPSHOT,
    })
  })

  it('confirms one exact latest revision with POST', async () => {
    const confirmed: ExtractionReviewConfirmResponse = {
      analysis_id: 'analysis-1',
      confirmed_revision_id: 'revision-2',
      confirmed_revision_number: 2,
      state: 'building_evidence',
    }
    const fetchMock = vi.fn().mockResolvedValue(mockResponse(confirmed, 202))
    vi.stubGlobal('fetch', fetchMock)

    expect(await confirmExtractionReview('analysis-1', 'revision-2')).toEqual(confirmed)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe(
      'http://localhost:8000/api/v1/analyses/analysis-1/extraction-review/confirm',
    )
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body as string)).toEqual({ revision_id: 'revision-2' })
  })
})
