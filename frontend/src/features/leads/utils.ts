import type { LeadOut } from '@/api/types'

export function getLeadSubtitle(lead: LeadOut): string {
  const lines = lead.description
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)

  const [, headline, location] = lines
  return [headline, location].filter(Boolean).join(' · ')
}

const SECTION_HEADERS = new Set(['About', 'Top skills', 'Services', 'Featured', 'Activity'])

export interface LeadProfileSection {
  label: string
  paragraphs: string[]
}

export interface LeadProfile {
  headline: string
  location: string
  meta: string[]
  sections: LeadProfileSection[]
}

function toParagraphs(bodyLines: string[]): string[] {
  const paragraphs: string[] = []
  let current: string[] = []
  for (const line of bodyLines) {
    if (line === '') {
      if (current.length) paragraphs.push(current.join(' '))
      current = []
    } else {
      current.push(line)
    }
  }
  if (current.length) paragraphs.push(current.join(' '))
  return paragraphs
}

export function parseLeadProfile(description: string): LeadProfile {
  const lines = description.split('\n').map((l) => l.trim())

  const headerEnd = lines.findIndex((l) => SECTION_HEADERS.has(l))
  const headerLines = (headerEnd === -1 ? lines : lines.slice(0, headerEnd)).filter(Boolean)
  const [, headline = '', location = '', ...meta] = headerLines

  const sections: LeadProfileSection[] = []
  if (headerEnd !== -1) {
    let i = headerEnd
    while (i < lines.length) {
      const label = lines[i]
      let j = i + 1
      while (j < lines.length && !SECTION_HEADERS.has(lines[j])) j++
      sections.push({ label, paragraphs: toParagraphs(lines.slice(i + 1, j)) })
      i = j
    }
  }

  return { headline, location, meta, sections }
}
