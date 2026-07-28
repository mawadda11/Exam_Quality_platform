import { apiGet, apiGetBlob, apiPostForm, apiPostJson, apiPutJson } from './client'
import type {
  AnalysisCreateRequest,
  AnalysisResponse,
  AnalysisScoreResponse,
  AssessmentRecordResponse,
  CloResponse,
  ExtractionReviewConfirmResponse,
  ExtractionReviewResponse,
  ExtractionReviewSnapshot,
  FindingResponse,
  ProgressResponse,
  QuestionResponse,
  ReanalysisCreateRequest,
  RecommendationResponse,
  ReportResponse,
  ReportLanguage,
  RuleCoverageAuditResponse,
  TopicResponse,
  UploadedFileResponse,
  UploadedFileType,
} from '../types/api'

export function createAnalysis(payload: AnalysisCreateRequest): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>('/analyses', payload)
}

export function getAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return apiGet<AnalysisResponse>(`/analyses/${analysisId}`)
}

export function listAnalyses(): Promise<AnalysisResponse[]> {
  return apiGet<AnalysisResponse[]>('/analyses')
}

export function uploadAnalysisFile(
  analysisId: string,
  fileType: UploadedFileType,
  file: File,
): Promise<UploadedFileResponse> {
  const form = new FormData()
  form.append('file_type', fileType)
  form.append('file', file)
  return apiPostForm<UploadedFileResponse>(`/analyses/${analysisId}/files`, form)
}

export function runAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>(`/analyses/${analysisId}/run`, {})
}

export function getAnalysisProgress(analysisId: string): Promise<ProgressResponse> {
  return apiGet<ProgressResponse>(`/analyses/${analysisId}/progress`)
}

export function retryAnalysis(analysisId: string): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>(`/analyses/${analysisId}/retry`, {})
}


export function getExtractionReview(analysisId: string): Promise<ExtractionReviewResponse> {
  return apiGet<ExtractionReviewResponse>(`/analyses/${analysisId}/extraction-review`)
}

export function saveExtractionReview(
  analysisId: string,
  baseRevisionId: string,
  snapshot: ExtractionReviewSnapshot,
): Promise<ExtractionReviewResponse> {
  return apiPutJson<ExtractionReviewResponse>(`/analyses/${analysisId}/extraction-review`, {
    base_revision_id: baseRevisionId,
    snapshot,
  })
}

export function confirmExtractionReview(
  analysisId: string,
  revisionId: string,
): Promise<ExtractionReviewConfirmResponse> {
  return apiPostJson<ExtractionReviewConfirmResponse>(
    `/analyses/${analysisId}/extraction-review/confirm`,
    { revision_id: revisionId },
  )
}

export function listQuestions(analysisId: string): Promise<QuestionResponse[]> {
  return apiGet<QuestionResponse[]>(`/analyses/${analysisId}/questions`)
}

export function listClos(analysisId: string): Promise<CloResponse[]> {
  return apiGet<CloResponse[]>(`/analyses/${analysisId}/clos`)
}

export function listTopics(analysisId: string): Promise<TopicResponse[]> {
  return apiGet<TopicResponse[]>(`/analyses/${analysisId}/topics`)
}

export function listAssessmentRecords(analysisId: string): Promise<AssessmentRecordResponse[]> {
  return apiGet<AssessmentRecordResponse[]>(`/analyses/${analysisId}/assessment-records`)
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === 'string'
}

function isFindingResponse(value: unknown): value is FindingResponse {
  if (typeof value !== 'object' || value === null) return false
  const finding = value as Record<string, unknown>
  return (
    typeof finding.id === 'string' &&
    typeof finding.analysis_id === 'string' &&
    typeof finding.requirement_id === 'string' &&
    typeof finding.rule_id === 'string' &&
    isNullableString(finding.recommendation_id) &&
    typeof finding.status === 'string' &&
    typeof finding.explanation === 'string' &&
    typeof finding.confidence === 'number' &&
    (finding.confidence_level === null ||
      finding.confidence_level === 'High' ||
      finding.confidence_level === 'Medium' ||
      finding.confidence_level === 'Low') &&
    (finding.evaluation_details === null ||
      (typeof finding.evaluation_details === 'object' &&
        finding.evaluation_details !== null)) &&
    typeof finding.evaluator_type === 'string' &&
    isNullableString(finding.ai_provider) &&
    isNullableString(finding.ai_model) &&
    isNullableString(finding.prompt_template_version) &&
    isNullableString(finding.kb_version) &&
    Array.isArray(finding.evidence)
  )
}

export function parseFindingResponses(value: unknown): FindingResponse[] {
  if (!Array.isArray(value) || !value.every(isFindingResponse)) {
    throw new Error('The server returned a malformed findings response.')
  }
  return value
}

export async function listFindings(analysisId: string): Promise<FindingResponse[]> {
  const response = await apiGet<unknown>(`/analyses/${analysisId}/findings`)
  return parseFindingResponses(response)
}

export function getRuleCoverage(analysisId: string): Promise<RuleCoverageAuditResponse> {
  return apiGet<RuleCoverageAuditResponse>(`/analyses/${analysisId}/rule-coverage`)
}

export function getAnalysisScore(analysisId: string): Promise<AnalysisScoreResponse> {
  return apiGet<AnalysisScoreResponse>(`/analyses/${analysisId}/score`)
}

export function listRecommendations(analysisId: string): Promise<RecommendationResponse[]> {
  return apiGet<RecommendationResponse[]>(`/analyses/${analysisId}/recommendations`)
}

export function generateReport(
  analysisId: string,
  language: ReportLanguage = 'en',
): Promise<ReportResponse> {
  return apiPostJson<ReportResponse>(`/analyses/${analysisId}/reports`, { language })
}

export function listReports(analysisId: string): Promise<ReportResponse[]> {
  return apiGet<ReportResponse[]>(`/analyses/${analysisId}/reports`)
}

export function downloadReportFile(reportId: string): Promise<Blob> {
  return apiGetBlob(`/reports/${reportId}/download`)
}

export function createReanalysis(
  analysisId: string,
  payload: ReanalysisCreateRequest = {},
): Promise<AnalysisResponse> {
  return apiPostJson<AnalysisResponse>(`/analyses/${analysisId}/reanalysis`, payload)
}

/** Triggers a browser download for an already-fetched Blob - a synthetic
 * anchor click is the standard way to do this once the file has to be
 * fetched manually (see apiGetBlob's docstring for why a plain <a href>
 * can't be used directly here). */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
