export type Rect = [number, number, number, number]

export function translateRectWithinPage(
  origin: Rect,
  deltaX: number,
  deltaY: number,
  pageWidth: number,
  pageHeight: number,
): Rect {
  const width = Math.max(0, origin[2] - origin[0])
  const height = Math.max(0, origin[3] - origin[1])
  const x0 = Math.max(0, Math.min(Math.max(0, pageWidth - width), origin[0] + deltaX))
  const y0 = Math.max(0, Math.min(Math.max(0, pageHeight - height), origin[1] + deltaY))
  return [x0, y0, x0 + width, y0 + height]
}
