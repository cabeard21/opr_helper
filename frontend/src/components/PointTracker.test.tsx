import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PointTracker } from './PointTracker'

describe('PointTracker', () => {
  it('shows remaining points while the list is under the limit', () => {
    render(<PointTracker pointLimit={2000} totalPoints={1500} />)

    expect(screen.getByText('1,500 / 2,000 pts')).toBeInTheDocument()
    expect(screen.getByText('500 pts remaining')).toBeInTheDocument()
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '75')
  })

  it('shows an over-limit warning once total points exceed the limit', () => {
    render(<PointTracker pointLimit={1000} totalPoints={1120} />)

    expect(screen.getByText('120 pts over')).toBeInTheDocument()
    expect(screen.getByText('Over limit')).toBeInTheDocument()
  })
})
