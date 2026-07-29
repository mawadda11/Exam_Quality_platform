import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { AnalysisResponse, AnalysisScoreResponse } from '../../types/api'
import { ResultsHeader } from './ResultsHeader'

const ANALYSIS: AnalysisResponse = {
  id: 'analysis-2',
  course: {
    id: 'course-1',
    code: 'CPIT-450',
    name: 'هندسة البرمجيات',
    department: null,
    program: null,
  },
  exam_type: 'Final',
  term: 'الفصل الثاني',
  state: 'completed',
  owner_user_id: 'user-1',
  predecessor_analysis_id: 'analysis-1',
  uploaded_files: [
    {
      id: 'file-1',
      file_type: 'exam',
      original_filename: 'اختبار.pdf',
      mime_type: 'application/pdf',
      size_bytes: 10,
      sha256_hash: 'a'.repeat(64),
      created_at: '2026-01-01T00:00:00Z',
    },
  ],
  exam_uploaded: true,
  tp153_uploaded: true,
  ready_for_analysis: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-07-26T00:00:00Z',
}

const SCORE: AnalysisScoreResponse = {
  analysis_id: 'analysis-2',
  score: null,
  label: 'Insufficient Evidence',
  denominator: 0,
  satisfied_count: 0,
  partially_satisfied_count: 0,
  not_satisfied_count: 0,
  not_verified_count: 1,
  not_applicable_count: 0,
}

describe('ResultsHeader', () => {
  it('shows real metadata, mixed-language isolation, predecessor context, and honest date label', () => {
    render(
      <MemoryRouter>
        <ResultsHeader
          analysis={ANALYSIS}
          score={{ status: 'ready', data: SCORE }}
          onRetryScore={vi.fn()}
        />
      </MemoryRouter>,
    )

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'هندسة البرمجيات',
    )
    expect(screen.getByText('اختبار.pdf').closest('bdi')).toHaveAttribute('dir', 'auto')
    expect(screen.getByText('الفصل الثاني').closest('bdi')).toHaveAttribute('dir', 'auto')
    expect(screen.getByText('Last updated')).toBeInTheDocument()
    expect(screen.getByText('Course Specification file')).toBeInTheDocument()
    expect(screen.queryByText('TP-153 file')).not.toBeInTheDocument()
    expect(screen.queryByText(/analysis date/i)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /analysis analysis-1/i }))
      .toHaveAttribute('href', '/analyses/analysis-1/results/overview')
    expect(screen.getByText('Insufficient Evidence')).toBeInTheDocument()
  })
})
