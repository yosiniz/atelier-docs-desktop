import { describe, expect, it } from 'vitest'
import { translateRectWithinPage } from './geometry'

describe('translateRectWithinPage', () => {
  it('moves a rectangle without changing its size', () => {
    expect(translateRectWithinPage([10, 20, 110, 60], 35, 15, 500, 700)).toEqual([45, 35, 145, 75])
  })

  it('keeps the rectangle inside the bottom-right page edge', () => {
    expect(translateRectWithinPage([10, 20, 110, 60], 900, 900, 500, 700)).toEqual([400, 660, 500, 700])
  })

  it('keeps the rectangle inside the top-left page edge', () => {
    expect(translateRectWithinPage([10, 20, 110, 60], -100, -100, 500, 700)).toEqual([0, 0, 100, 40])
  })
})
