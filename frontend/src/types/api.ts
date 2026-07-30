export type ExamType = 'Midterm' | 'Final'

export type UploadedFileType = 'exam' | 'tp153'

export type Locale = 'ar' | 'en'
export type ReportLanguage = Locale

export type ProcessingStage =
  | 'queued'
  | 'validating'
  | 'extracting_exam'
  | 'extracting_tp153'
  | 'review_ready'
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
  capability_version?: string
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
  failed_stage: ProcessingStage | null
  error_code: string | null
  can_retry: boolean
  updated_at: string
}

export type SemanticConfidenceLevel = 'High' | 'Medium' | 'Low'

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

export type SupportingMaterialType = 'figure' | 'table' | 'code_block'
export type SupportingAnnotationType = 'caption' | 'label'
export type ReferenceTargetType = SupportingMaterialType | 'question'
export type ReferenceResolutionStatus = 'resolved' | 'ambiguous' | 'unresolved'
export type AssociationBasis = 'exact_label' | 'proximity_support'

export interface SupportingMaterialResponse {
  id: string
  analysis_id: string
  question_id: string | null
  source_document: UploadedFileType
  material_type: SupportingMaterialType
  page_number: number
  source_text: string
  geometry: Record<string, unknown> | null
  confidence: number
  extraction_method: string
  created_at: string
}

export interface SupportingMaterialAnnotationResponse {
  id: string
  analysis_id: string
  material_id: string | null
  source_document: UploadedFileType
  annotation_type: SupportingAnnotationType
  original_text: string
  normalized_label: string | null
  page_number: number
  geometry: Record<string, unknown> | null
  confidence: number
  extraction_method: string
  created_at: string
}

export interface ReferenceAssociationResponse {
  id: string
  target_material_id: string | null
  target_question_id: string | null
  review_revision_id: string | null
  basis: AssociationBasis
  confidence: number
  proximity_distance: number | null
  exact_label_match: boolean
  selected: boolean
  ambiguity_reason: string | null
}

export interface DocumentReferenceResponse {
  id: string
  analysis_id: string
  question_id: string | null
  source_document: UploadedFileType
  target_type: ReferenceTargetType
    original_text: string
    target_label: string
    normalized_target_label: string
  page_number: number
  geometry: Record<string, unknown> | null
  confidence: number
  extraction_method: string
  resolution_status: ReferenceResolutionStatus
  association_candidates: ReferenceAssociationResponse[]
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
  | 'exam_metadata'
  | 'figure'
  | 'table'
  | 'code_block'
  | 'caption'
  | 'label'
  | 'explicit_reference'

export interface FindingEvidenceRef {
  id: string
  source_document: UploadedFileType
  evidence_type: string
  page_number: number
  item_reference: string
}

export interface FindingItemJudgmentDetails {
  source_evidence_id: string
  target_evidence_ids: string[]
  status: AcademicStatus
  reasoning: string
}

export interface FindingEvaluationDetails {
  schema_version: 1
  decision: AcademicStatus
  evidence_used: string[]
  reasoning: string
  recommendation: string | null
  confidence_basis: string[]
  item_judgments: FindingItemJudgmentDetails[]
  retrieved_knowledge_ids: string[]
}

export interface FindingResponse {
  id: string
  analysis_id: string
  requirement_id: string
  rule_id: string
  recommendation_id: string | null
  status: AcademicStatus
  explanation: string
  confidence: number
  confidence_level: SemanticConfidenceLevel | null
  evaluation_details: FindingEvaluationDetails | null
  evaluator_type: string
  ai_provider: string | null
  ai_model: string | null
  prompt_template_version: string | null
  kb_version: string | null
  created_at: string
  evidence: FindingEvidenceRef[]
  requirement_name: string
  dimension: string
  source_type: string
  officiality: string
}

export type RuleRuntimeDisposition =
  | 'evaluated'
  | 'conditional_capability_gap'
  | 'unsupported'
  | 'not_run'

export interface RuleCoverageEntryResponse {
  requirement_id: string
  rule_id: string
  requirement_name: string
  rule_name: string
  support_status: 'supported' | 'partially_supported' | 'unsupported'
  evaluation_mode: 'deterministic' | 'semantic_or_hybrid' | 'no_authorized_method'
  design_disposition: 'design_authorized' | 'deferred'
  runtime_disposition: RuleRuntimeDisposition
  finding_status: AcademicStatus | null
  evaluator_type: string | null
  implemented_milestone: string | null
  reason: string | null
  planned_milestone_or_dependency: string | null
}

export interface RuleCoverageAuditResponse {
  analysis_id: string
  capability_version?: string
  scope: 'exam_facing_rules'
  total_rules: number
  evaluated_rules: number
  conditional_capability_gap_rules: number
  unsupported_rules: number
  not_run_rules: number
  runtime_integrity_ok: boolean
  entries: RuleCoverageEntryResponse[]
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
  language: ReportLanguage
  kb_version: string
  capability_version?: string | null
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

export type ReportLibraryPersistedStatus =
  | 'available'
  | 'not_generated'
  | 'outdated'
  | 'insufficient_evidence'

export type ReportLibraryStatus =
  | ReportLibraryPersistedStatus
  | 'generation_failed'

export type ReportLibrarySort = 'newest' | 'oldest' | 'course' | 'score'

export interface ReportLibraryAnalysisResponse {
  id: string
  course_code: string
  course_name: string
  exam_type: ExamType
  term: string
  state: ProcessingStage
  capability_version: string | null
  predecessor_analysis_id: string | null
  created_at: string
  updated_at: string
}

export interface ReportLibraryItemResponse {
  status: ReportLibraryPersistedStatus
  analysis: ReportLibraryAnalysisResponse
  report: ReportResponse | null
}

export interface ReportLibraryPageResponse {
  items: ReportLibraryItemResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ReportLibraryQuery {
  q?: string
  status?: ReportLibraryPersistedStatus
  exam_type?: ExamType
  language?: ReportLanguage
  sort?: ReportLibrarySort
  page?: number
  page_size?: number
}


export interface ExtractionReviewGeometry {
  x0: number
  top: number
  x1: number
  bottom: number
}

export interface ExtractionReviewQuestion {
  source_record_id: string
  included: boolean
  parent_source_record_id: string | null
  number_label: string
  question_text: string
  page_number: number
  marks: number | null
  sequence: number
  extraction_confidence: number
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewEvidence {
  source_record_id: string
  included: boolean
  question_source_record_id: string | null
  source_document: UploadedFileType
  evidence_type: string
  page_number: number
  item_reference: string
  extracted_text: string
  extraction_confidence: number
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewClo {
  source_record_id: string
  included: boolean
  code: string
  text: string
  program_outcome_reference: string | null
  page_number: number
  extraction_confidence: number
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewTopic {
  source_record_id: string
  included: boolean
  code: string | null
  text: string
  expected_hours: number | null
  page_number: number
  extraction_confidence: number
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewAssessmentRecord {
  source_record_id: string
  included: boolean
  method: string
  activity: string | null
  percentage: number | null
  page_number: number
  extraction_confidence: number
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewSupportingMaterial {
  source_record_id: string
  included: boolean
  question_source_record_id: string | null
  source_document: UploadedFileType
  material_type: SupportingMaterialType
  source_text: string
  page_number: number
  extraction_confidence: number
  extraction_method: string
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewSupportingAnnotation {
  source_record_id: string
  included: boolean
  material_source_record_id: string | null
  source_document: UploadedFileType
  annotation_type: SupportingAnnotationType
  original_text: string
  normalized_label: string | null
  page_number: number
  extraction_confidence: number
  extraction_method: string
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewDocumentReference {
  source_record_id: string
  included: boolean
  question_source_record_id: string | null
  source_document: UploadedFileType
  target_type: ReferenceTargetType
  original_text: string
  target_label: string
  normalized_target_label: string
  resolution_status: ReferenceResolutionStatus
  page_number: number
  extraction_confidence: number
  extraction_method: string
  geometry: ExtractionReviewGeometry | null
}

export interface ExtractionReviewReferenceAssociation {
  source_record_id: string
  reference_source_record_id: string
  target_material_source_record_id: string | null
  target_question_source_record_id: string | null
  basis: AssociationBasis
  extraction_confidence: number
  proximity_distance: number | null
  exact_label_match: boolean
  selected: boolean
  ambiguity_reason: string | null
}

export interface ExtractionReviewSnapshot {
  schema_version: 1
  questions: ExtractionReviewQuestion[]
  evidence: ExtractionReviewEvidence[]
  clos: ExtractionReviewClo[]
  topics: ExtractionReviewTopic[]
  assessment_records: ExtractionReviewAssessmentRecord[]
  supporting_materials?: ExtractionReviewSupportingMaterial[]
  supporting_annotations?: ExtractionReviewSupportingAnnotation[]
  document_references?: ExtractionReviewDocumentReference[]
  reference_associations?: ExtractionReviewReferenceAssociation[]
}

export type ExtractionReviewCollection =
  | 'questions'
  | 'evidence'
  | 'clos'
  | 'topics'
  | 'assessment_records'
  | 'supporting_materials'
  | 'supporting_annotations'
  | 'document_references'
  | 'reference_associations'
  | 'review'

export interface ExtractionReviewWarning {
  code: string
  severity: 'info' | 'warning'
  collection: ExtractionReviewCollection
  source_record_id: string | null
  message: string
}

export interface ExtractionReviewResponse {
  analysis_id: string
  revision_id: string
  revision_number: number
  created_at: string
  snapshot: ExtractionReviewSnapshot
  original_snapshot: ExtractionReviewSnapshot
  confirmed_revision_id: string | null
  is_confirmed: boolean
  can_edit: boolean
  can_confirm: boolean
  warnings: ExtractionReviewWarning[]
  confirmation_blockers: string[]
}

export interface ExtractionReviewConfirmResponse {
  analysis_id: string
  confirmed_revision_id: string
  confirmed_revision_number: number
  state: ProcessingStage
}

export interface FacultyUserResponse {
  id: string
  email: string
  display_name: string
  institution: string | null
  department: string | null
  user_type: 'Faculty Member'
  preferred_language: Locale
  email_verified: boolean
  created_at: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name: string
  institution?: string | null
  department?: string | null
  preferred_language?: Locale
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthSessionResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: FacultyUserResponse
}

export interface PasswordResetRequestResponse {
  message: string
  debug_reset_token: string | null
}

export interface PasswordResetConfirmRequest {
  token: string
  new_password: string
}

export interface MessageResponse {
  message: string
}
