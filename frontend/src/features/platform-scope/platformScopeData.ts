export interface EvaluationScopeItem {
  ruleId: string
  title: string
  description: string
}

export const SUPPORTED_EVALUATION_SCOPE: EvaluationScopeItem[] = [
  {
    ruleId: 'RULE001',
    title: 'Question-to-CLO mapping',
    description: 'Relates exam questions to documented course learning outcomes using confirmed evidence.',
  },
  {
    ruleId: 'RULE002',
    title: 'CLO relevance',
    description: 'Checks whether question content is relevant to the confirmed CLO relationship.',
  },
  {
    ruleId: 'RULE003',
    title: 'Assessment-method consistency',
    description: 'Checks consistency with the assessment methods documented in TP-153.',
  },
  {
    ruleId: 'RULE004',
    title: 'Question-format suitability',
    description: 'Reviews whether the question format is suitable for the intended response.',
  },
  {
    ruleId: 'RULE005',
    title: 'Applicable CLO coverage',
    description: 'Summarizes which documented applicable CLOs are covered by the exam.',
  },
  {
    ruleId: 'RULE007',
    title: 'Question-to-topic alignment',
    description: 'Relates questions to documented course topics when usable topic evidence is available.',
  },
  {
    ruleId: 'RULE008',
    title: 'Out-of-scope content',
    description: 'Flags question content that is not supported by the confirmed course evidence.',
  },
  {
    ruleId: 'RULE009',
    title: 'Applicable topic coverage',
    description: 'Summarizes coverage of documented topics designated for the exam.',
  },
  {
    ruleId: 'RULE011',
    title: 'Clear task statement',
    description: 'Reviews whether the required task is stated clearly.',
  },
  {
    ruleId: 'RULE012',
    title: 'Unambiguous wording',
    description: 'Reviews question wording for avoidable ambiguity.',
  },
  {
    ruleId: 'RULE013',
    title: 'Complete question information',
    description: 'Checks whether the question contains the information needed to respond.',
  },
  {
    ruleId: 'RULE018',
    title: 'Correct total marks',
    description: 'Checks deterministic marks arithmetic when reliable marks evidence is available.',
  },
  {
    ruleId: 'RULE019',
    title: 'Consistent numbering',
    description: 'Checks the extracted question-numbering structure for consistency.',
  },
  {
    ruleId: 'RULE021',
    title: 'Complete instructions',
    description: 'Reviews whether required exam or question instructions are complete.',
  },
]

export const LIMITED_EVALUATION_SCOPE: EvaluationScopeItem[] = [
  {
    ruleId: 'RULE006',
    title: 'CLO coverage distribution',
    description:
      'The current version handles zero or one applicable CLO. Cases with two or more applicable CLOs require an approved concentration method before the system can judge distribution.',
  },
]

export const PLANNED_EVALUATION_SCOPE: EvaluationScopeItem[] = [
  {
    ruleId: 'RULE014',
    title: 'Referenced material availability',
    description: 'Planned structured extraction of referenced figures, tables, code, and attachments.',
  },
  {
    ruleId: 'RULE015',
    title: 'Supporting material legibility',
    description: 'Requires an approved visual-quality method and governed legibility thresholds.',
  },
  {
    ruleId: 'RULE016',
    title: 'Supporting material association',
    description: 'Planned layout-aware linking between questions and the correct supporting material.',
  },
  {
    ruleId: 'RULE017',
    title: 'Visible marks',
    description: 'Requires an approved institutional policy defining where marks must be displayed.',
  },
  {
    ruleId: 'RULE020',
    title: 'Exam identification',
    description: 'Requires a configurable institutional list of mandatory exam-identification fields.',
  },
  {
    ruleId: 'RULE022',
    title: 'Resolvable cross-references',
    description: 'Planned layout-aware checking of references such as figures, tables, and other questions.',
  },
]
