import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ResponsiveTable } from './ResponsiveTable'

describe('ResponsiveTable', () => {
  it('preserves native table, caption, header, and row semantics', () => {
    render(
      <ResponsiveTable caption="Analysis history">
        <thead>
          <tr>
            <th scope="col">Course</th>
            <th scope="col">State</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">CS101</th>
            <td>Completed</td>
          </tr>
        </tbody>
      </ResponsiveTable>,
    )

    expect(screen.getByRole('region', { name: 'Analysis history' })).toHaveAttribute(
      'tabindex',
      '0',
    )
    expect(screen.getByRole('table', { name: 'Analysis history' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Course' })).toHaveAttribute('scope', 'col')
    expect(screen.getByRole('rowheader', { name: 'CS101' })).toHaveAttribute('scope', 'row')
  })
})
