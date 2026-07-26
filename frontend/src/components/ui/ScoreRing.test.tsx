import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ScoreRing } from './ScoreRing'

describe('ScoreRing', () => {
  it('shows the exact numeric score and verified applicable denominator', () => {
    render(<ScoreRing score="78.60" denominator={5} />)

    expect(screen.getByText('78.60%')).toBeVisible()
    expect(screen.getByText('Based on 5 verified applicable rules')).toBeVisible()
    expect(screen.getByRole('img')).toHaveAccessibleName(
      'Overall Exam Quality Score: 78.60%. Based on 5 verified applicable rules.',
    )
  })

  it('shows Insufficient Evidence instead of a zero score for a null score', () => {
    render(<ScoreRing score={null} denominator={0} />)

    expect(screen.getByText('Insufficient Evidence')).toBeVisible()
    expect(screen.queryByText('0%')).not.toBeInTheDocument()
    expect(screen.getByRole('img')).toHaveAccessibleName(
      'Overall Exam Quality Score: Insufficient Evidence. Based on 0 verified applicable rules.',
    )
  })
})
