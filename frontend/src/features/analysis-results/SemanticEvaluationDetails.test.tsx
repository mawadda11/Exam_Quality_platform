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
  explanation: 'Questions were mapped to controlled CLO evidence.',
  confidence: 1,
  confidence_level: 'High',
  evaluation_details: {
    schema_version: 1,
    decision: 'Satisfied',
    evidence_used: ['question-evidence', 'clo-evidence'],
    reasoning: 'The confirmed question evidence is related to the confirmed CLO.',
    recommendation: null,
    confidence_basis: ['All required question items were judged.'],
    item_judgments: [
      {
        source_evidence_id: 'question-evidence',
        target_evidence_ids: ['clo-evidence'],
        status: 'Satisfied',
        reasoning: 'The question directly addresses the controlled CLO concept.',
      },
    ],
    retrieved_knowledge_ids: ['REQ001', 'RULE001'],
  },
  evaluator_type: 'semantic_ai',
  ai_provider: 'fake',
  ai_model: 'fake-semantic-v1',
  prompt_template_version: 'semantic-rule-v1',
  kb_version: '1.0',
  created_at: '2026-07-27T00:00:00Z',
  evidence: [
    {
      id: 'question-evidence',
      source_document: 'exam',
      evidence_type: 'question_text',
      page_number: 1,
      item_reference: 'Q1',
    },
    {
      id: 'clo-evidence',
      source_document: 'tp153',
      evidence_type: 'clo',
      page_number: 3,
      item_reference: 'CLO1',
    },
  ],
  requirement_name: 'Question-to-CLO Mapping',
  dimension: 'CLO Alignment',
  source_type: 'Derived Exam Requirement',
  officiality: 'Derived',
}

describe('SemanticEvaluationDetails', () => {
  it('labels retained relationship judgments as AI-derived advisory output', () => {
    render(<SemanticEvaluationDetails finding={FINDING} />)

    expect(screen.getByText('AI-derived advisory relationship')).toBeInTheDocument()
    expect(screen.getByText(/not an official TP-153 mapping/i)).toBeInTheDocument()
    expect(screen.getByText(/Q1 · Exam page 1 · question_text/i)).toBeInTheDocument()
    expect(screen.getByText(/CLO1 · TP-153 page 3 · clo/i)).toBeInTheDocument()
    expect(screen.getByText(/directly addresses the controlled CLO concept/i))
      .toBeInTheDocument()
    expect(screen.getByText(/All required question items were judged/i))
      .toBeInTheDocument()
    expect(screen.getByText(/Controlled KB references/i)).toHaveTextContent('REQ001, RULE001')
  })

  it('does not relabel a target-free judgment as a mapping', () => {
    const finding: FindingResponse = {
      ...FINDING,
      rule_id: 'RULE011',
      evaluation_details: {
        ...FINDING.evaluation_details!,
        item_judgments: [
          {
            source_evidence_id: 'question-evidence',
            target_evidence_ids: [],
            status: 'Satisfied',
            reasoning: 'The wording is concise.',
          },
        ],
      },
    }

    render(<SemanticEvaluationDetails finding={finding} />)

    expect(screen.getByText('Governed semantic item judgment')).toBeInTheDocument()
    expect(screen.queryByText('AI-derived advisory relationship')).not.toBeInTheDocument()
    expect(screen.getByText(/No target relationship was asserted/i)).toBeInTheDocument()
  })
})
