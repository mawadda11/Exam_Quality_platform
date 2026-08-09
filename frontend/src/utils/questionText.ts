const REGEX_ESCAPE = /[.*+?^${}()|[\]\\]/g

function escapeRegex(value: string): string {
  return value.replace(REGEX_ESCAPE, '\\$&')
}

function flexibleQuestionLabelPattern(numberLabel: string): string {
  return Array.from(numberLabel.trim())
    .filter((character) => !/\s/u.test(character))
    .map((character) => escapeRegex(character))
    .join('\\s*')
}

/**
 * Returns the human-facing question text without a duplicated leading question
 * identifier. PDF extraction can preserve labels with different visual spacing
 * (for example `Q1.1` vs `Q 1.1`). Keeping the identifier in the canonical
 * source is useful for provenance, but rendering it again can force an LTR base
 * direction before an Arabic sentence and produce confusing mixed-direction
 * display.
 *
 * This helper is language-agnostic: it only removes the known number label at
 * the beginning of the text, allowing harmless whitespace differences between
 * its characters. It does not rewrite the source text or technical terms.
 */
export function displayQuestionText(value: string, numberLabel: string): string {
  const trimmedLabel = numberLabel.trim()
  if (!trimmedLabel) return value.trimStart()

  const flexibleLabel = flexibleQuestionLabelPattern(trimmedLabel)
  if (!flexibleLabel) return value.trimStart()

  const pattern = new RegExp(
    `^\\s*(?:(?:question|السؤال)\\s*)?${flexibleLabel}(?=\\s|[:.)_\\-–—]|$)\\s*(?:[:.)_\\-–—]+\\s*)?`,
    'iu',
  )

  return value.replace(pattern, '').trimStart()
}
