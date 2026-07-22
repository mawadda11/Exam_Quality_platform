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
  uploaded_files: UploadedFileResponse[]
  exam_uploaded: boolean
  tp153_uploaded: boolean
  ready_for_analysis: boolean
  created_at: string
  updated_at: string
}

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
}
