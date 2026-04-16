/**
 * Pure string transforms for web "参考文献" blocks (no React).
 * Kept separate from source-references.tsx so Vitest can import without jsx.
 */

const WEB_BIBLIOGRAPHY_TITLE = '(?:参考文献|Web References|References)'

/** Optional fullwidth/colon after title — models vary */
const WEB_BIBLIOGRAPHY_HEADING = new RegExp(
  `^#{1,3}\\s*${WEB_BIBLIOGRAPHY_TITLE}[:：]?\\s*$`,
  'i'
)

/** `m` = per line, `g` = replace every such heading in the message */
const WEB_BIBLIOGRAPHY_BOLD_LINE =
  /^\s*\*{1,2}\s*(参考文献|Web References|References)[:：]?\s*\*{1,2}\s*$/gim

/** ZWSP etc. can break heading regex matches when copied from PDF/Word */
function stripInvisible(s: string): string {
  return s.replace(/[\u200B-\u200D\uFEFF]/g, '')
}

function normalizeBibliographyMarkdownHeadings(text: string): string {
  return text.replace(WEB_BIBLIOGRAPHY_BOLD_LINE, (_, title: string) => `## ${title.trim()}`)
}


function lineIsMarkdownHttpLinkLine(line: string): boolean {
  const t = line.replace(/\r$/, '').trim()
  if (!t) return false
  if (/^\d+\.\s/.test(t)) return false
  const body = t.replace(/^[-*+]\s+/, '')
  if (/^\d+\.\s/.test(body.trim())) return false
  return /\[([^\]]*)\]\(\s*https?:\/\//.test(body)
}

/** GFM autolink: whole line is one URL (optional angle brackets) */
function lineIsBareHttpUrlLine(line: string): boolean {
  const t = line.replace(/\r$/, '').trim()
  if (!t) return false
  if (/^\d+\.\s/.test(t)) return false
  const inner = t.replace(/^[-*+]\s+/, '').replace(/^<|>$/g, '').trim()
  return /^https?:\/\/\S+$/.test(inner)
}

function formatBareUrlLine(trimmedBody: string): string {
  const u = trimmedBody
    .replace(/^[-*+]\s+/, '')
    .replace(/^<|>$/g, '')
    .trim()
  return `[${u}](${u})`
}

/**
 * Largest n in markdown links [n](https://...) — web citations from the model.
 */
export function getMaxWebCitationNumber(text: string): number {
  const re = /\[(\d+)]\(\s*https?:\/\//g
  let max = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) {
    const n = parseInt(m[1], 10)
    if (!Number.isNaN(n) && n > max) max = n
  }
  return max
}

/**
 * Under 参考文献 / Web References / References, ensure ordered list (1. 2. …).
 */
export function ensureNumberedWebBibliographySection(text: string): string {
  const normalized = normalizeBibliographyMarkdownHeadings(stripInvisible(text))
  const lines = normalized.split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const rawLine = lines[i]
    const line = rawLine.replace(/\r$/, '')
    if (WEB_BIBLIOGRAPHY_HEADING.test(line.trim())) {
      const m = line.trim().match(/^#{1,3}\s*(.+)$/)
      out.push(m ? `## ${m[1].replace(/[:：]\s*$/, '').trim()}` : line)
      i++
      let n = 1
      while (i < lines.length) {
        const rawL = lines[i]
        const L = rawL.replace(/\r$/, '')
        if (/^##\s/.test(L) && !/^###/.test(L) && !WEB_BIBLIOGRAPHY_HEADING.test(L.trim())) {
          break
        }
        const trimmedForLink = L.trim()
        if (lineIsMarkdownHttpLinkLine(L)) {
          const leading = L.match(/^(\s*)/)?.[1] ?? ''
          const trimmed = L.trim()
          const body = trimmed.replace(/^[-*+]\s+/, '')
          out.push(`${leading}${n}. ${body}`)
          n++
        } else if (lineIsBareHttpUrlLine(L)) {
          const leading = L.match(/^(\s*)/)?.[1] ?? ''
          out.push(`${leading}${n}. ${formatBareUrlLine(trimmedForLink)}`)
          n++
        } else {
          out.push(rawL)
        }
        i++
      }
      continue
    }
    out.push(rawLine)
    i++
  }
  return out.join('\n')
}
