import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { FindingResponse } from '../../types/api'
import { SemanticEvaluationDetails } from './SemanticEvaluationDetails'

const FINDING: FindingResponse = {
  id: 'finding-1',
  analysis_id: 'analysis-1',
  requirement_id: 'REQ001',
  rule_id: 'RULE001',
  recommendation_id: null,
  status: 'Satisfied',
  explanation: 'Questions were mapped to Course Specification evidence.',
  confidence: 1,
  confidence_level: 'High',
  evaluation_details: {
    schema_version: 1,
    decision: 'Satisfied',
    evidence_used: ['question-evidence', 'clo-evidence'],
    reasoning: 'The question is related to the CLO.',
    recommendation: null,
    confidence_basis: ['All required question items were judged.'],
    item_judgments: [
      {
        source_evidence_id: 'question-evidence',
        target_evidence_ids: ['clo-evidence'],
        status: 'Satisfied',
        reasoning: 'The question addresses the CLO concept.',
      },
    ],
    retrieved_knowledge_ids: ['REQ001', 'RULE001'],
  },
  evaluator_type: 'semantic_ai',
  ai_provider: 'internal-provider',
  ai_model: 'internal-model',
  prompt_template_version: 'internal-prompt',
  kb_version: 'internal-kb',
  created_at: '2026-07-27T00:00:00Z',
  evidence: [],
  requirement_name: 'Question-to-CLO Mapping',
  dimension: 'CLO Alignment',
  source_type: 'Derived Exam Requirement',
  officiality: 'Derived',
}

describe('SemanticEvaluationDetails', () => {
  it('shows only faculty-facing determination details', () => {
    render(<SemanticEvaluationDetails finding={FINDING} />)

    expect(screen.getByText('Semantic content analysis')).toBeInTheDocument()
    expect(screen.getByText('Evidence reliability')).toBeInTheDocument()
    expect(screen.getByText('Suggested relationship')).toBeInTheDocument()
    expect(screen.getByText(/analytical suggestion for review/i)).toBeInTheDocument()
    expect(screen.queryByText(/internal-provider|internal-model|internal-prompt|internal-kb/))
      .not.toBeInTheDocument()
    expect(screen.queryByText(/REQ001|RULE001/)).not.toBeInTheDocument()
    expect(screen.queryByText(/audit references/i)).not.toBeInTheDocument()
  })

  it('labels deterministic evaluation in plain language', () => {
    render(
      <SemanticEvaluationDetails
        finding={{
          ...FINDING,
          rule_id: 'RULE018',
          dimension: 'Marks and Totals',
          evaluator_type: 'deterministic_rule',
          evaluation_details: null,
          confidence_level: null,
        }}
      />,
    )

    expect(screen.getByText('Rule-based automated check')).toBeInTheDocument()
    expect(screen.queryByText('Suggested relationship')).not.toBeInTheDocument()
  })
})
