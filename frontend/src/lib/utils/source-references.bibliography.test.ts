import { describe, it, expect } from 'vitest'
import {
  ensureNumberedWebBibliographySection,
  getMaxWebCitationNumber
} from './source-references-bibliography'

describe('ensureNumberedWebBibliographySection', () => {
  it('numbers ### 参考文献 with bullet markdown links', () => {
    const input = `正文 [1](https://example.com/a)

### 参考文献

- [Wiki - AMPS](https://en.wikipedia.org/wiki/AMPS)
- [Zehao](https://zehao.com/p)
`
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('1. [Wiki - AMPS](https://en.wikipedia.org/wiki/AMPS)')
    expect(out).toContain('2. [Zehao](https://zehao.com/p)')
    expect(out).toMatch(/## 参考文献/)
  })

  it('numbers ## 参考文献 with plain link lines (no bullet)', () => {
    const input = `## 参考文献

[One](https://a.com/x)
[Two](https://b.com/y)
`
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('1. [One](https://a.com/x)')
    expect(out).toContain('2. [Two](https://b.com/y)')
  })

  it('handles CRLF', () => {
    const input =
      '### 参考文献\r\n\r\n- [A](https://a.com)\r\n'
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('1. [A](https://a.com)')
  })

  it('normalizes **参考文献** bold line to ## and numbers following links', () => {
    const input = `**参考文献**

- [X](https://x.com)
`
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('## 参考文献')
    expect(out).toContain('1. [X](https://x.com)')
  })

  it('does not re-number lines that already have 1. 2.', () => {
    const input = `## 参考文献

1. [A](https://a.com)
2. [B](https://b.com)
`
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('1. [A](https://a.com)')
    expect(out).toContain('2. [B](https://b.com)')
  })

  it('matches heading with fullwidth colon 参考文献：', () => {
    const input = `## 参考文献：

[U](https://u.com)
`
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('1. [U](https://u.com)')
  })

  it('numbers bare URL lines (GFM autolink)', () => {
    const input = `### 参考文献

https://a.com/page
https://b.com/x
`
    const out = ensureNumberedWebBibliographySection(input)
    expect(out).toContain('1. [https://a.com/page](https://a.com/page)')
    expect(out).toContain('2. [https://b.com/x](https://b.com/x)')
  })
})

describe('getMaxWebCitationNumber', () => {
  it('returns max n from [n](https://...) in body', () => {
    expect(
      getMaxWebCitationNumber('x [1](https://a) y [5](https://b) [2](https://c)')
    ).toBe(5)
  })
})
