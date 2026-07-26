import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Button } from './Button'

describe('Button', () => {
  it.each(['primary', 'secondary', 'ghost'] as const)(
    'supports the %s variant',
    (variant) => {
      render(<Button variant={variant}>Continue</Button>)
      expect(screen.getByRole('button', { name: 'Continue' })).toHaveClass(
        `ui-button--${variant}`,
      )
    },
  )

  it('is disabled and exposes a loading state while loading', () => {
    render(
      <Button isLoading loadingLabel="Saving…">
        Save
      </Button>,
    )
    const button = screen.getByRole('button', { name: 'Saving…' })
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('aria-busy', 'true')
  })

  it('honors an explicitly disabled state', () => {
    render(<Button disabled>Continue</Button>)
    expect(screen.getByRole('button', { name: 'Continue' })).toBeDisabled()
  })
})
