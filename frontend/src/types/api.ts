export type ExamType = 'Midterm' | 'Final'

export type UploadedFileType = 'exam' | 'tp153'

export type ProcessingStage =
  | 'queued'
  | 'validating'
  | 'extracting_exam'
  | 'extracting_tp153'
  | 'building_evidence'
  | 'retrieving_knowledge'
  | 'applying_rules'
  | 'generating_report'
  | 'completed'
  | 'failed'

export interface CourseInput {
  code: string
  name: string
  department?: string | null
  program?: string | null
}

export interface CourseResponse {
  id: string
  code: string
  name: string
  department: string | null
  program: string | null
}

export interface UploadedFileResponse {
  id: string
  file_type: UploadedFileType
  original_filename: string
  mime_type: string
  size_bytes: number
  sha256_hash: string
  created_at: string
}

export interface AnalysisCreateRequest {
  course: CourseInput
  exam_type: ExamType
  term: string
}

export interface AnalysisResponse {
  id: string
  course: CourseResponse
  exam_type: ExamType
  term: string
  state: ProcessingStage
  owner_user_id: string
  predecessor_analysis_id: string | null
  uploaded_files: UploadedFileResponse[]
  exam_uploaded: boolean
  tp153_uploaded: boolean
  ready_for_analysis: boolean
  created_at: string
  updated_at: string
}

/** course/exam_type/term are always inherited from the predecessor - see
 * backend/app/schemas/analysis.py's ReanalysisCreateRequest docstring.
 * reuse_tp153 defaults to true server-side when the body is omitted. */
export interface ReanalysisCreateRequest {
  reuse_tp153?: boolean
}

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
}

export interface ProgressResponse {
  analysis_id: string
  state: ProcessingStage
  message: string | null
  updated_at: string
}

export type AcademicStatus =
  | 'Satisfied'
  | 'Partially Satisfied'
  | 'Not Satisfied'
  | 'Not Verified'
  | 'Not Applicable'

export interface QuestionResponse {
  id: string
  analysis_id: string
  parent_question_id: string | null
  number_label: string
  question_text: string
  page_number: number
  marks: number | null
  sequence: number
  confidence: number
  geometry: Record<string, unknown> | null
  created_at: string
}

export interface CloResponse {
  id: string
  analysis_id: string
  code: string
  text: string
  program_outcome_reference: string | null
  page_number: number
  confidence: number
  geometry: Record<string, unknown> | null
  created_at: string
}

export interface TopicResponse {
  id: string
  analysis_id: string
  code: string | null
  text: string
  expected_hours: number | null
  page_number: number
  confidence: number
  geometry: Record<string, unknown> | null
  created_at: string
}

export interface AssessmentRecordResponse {
  id: string
  analysis_id: string
  method: string
  activity: string | null
  percentage: number | null
  page_number: number
  confidence: number
  geometry: Record<string, unknown> | null
  created_at: string
}

/** Known `evidence_type` values produced by the extraction/rule-engine
 * pipeline (backend/app/services/extraction/*, backend/app/services/rules/*).
 * Not a closed backend contract - evidence_type is a free string column, so
 * display code must fall back gracefully for any value not listed here. */
export type KnownEvidenceType =
  | 'question_text'
  | 'marks'
  | 'declared_total'
  | 'instructions'
  | 'clo'
  | 'topic'
  | 'assessment_record'
  | 'missing_section'

export interface FindingEvidenceRef {
  id: string
  source_document: UploadedFileType
  evidence_type: string
  page_number: number
  item_reference: string
}

export interface FindingResponse {
  id: string
  analysis_id: string
  requirement_id: string
  rule_id: string
  status: AcademicStatus
  explanation: string
  confidence: number
  evaluator_type: string
  created_at: string
  evidence: FindingEvidenceRef[]
  requirement_name: string
  dimension: string
  source_type: string
  officiality: string
}

export interface AnalysisScoreResponse {
  analysis_id: string
  score: string | null
  label: string | null
  denominator: number
  satisfied_count: number
  partially_satisfied_count: number
  not_satisfied_count: number
  not_verified_count: number
  not_applicable_count: number
}

export interface RecommendationResponse {
  finding_id: string
  requirement_id: string
  rule_id: string
  status: AcademicStatus
  recommendation_id: string
  title: string
  text: string
  target_user: string
  recommendation_type: string
}

export type ReportFormat = 'pdf'

export interface ReportResponse {
  id: string
  analysis_id: string
  format: ReportFormat
  kb_version: string
  score: string | null
  score_label: string | null
  denominator: number
  satisfied_count: number
  partially_satisfied_count: number
  not_satisfied_count: number
  not_verified_count: number
  not_applicable_count: number
  size_bytes: number
  created_at: string
}
