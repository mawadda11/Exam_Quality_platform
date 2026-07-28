import { useI18n } from '../../i18n/I18nProvider'
import { presentGovernedLabel } from '../../i18n/governedPresentation'

export { StatusBadge } from '../../components/ui/StatusBadge'

/** CLAUDE.md: "Do not present derived project rules as official
 * quotations." source_type is always "Derived Exam Requirement" or "System
 * Requirement" (04_requirements.xlsx) - never itself an official standard
 * quotation - so labelling it plainly is sufficient to honor that rule. */
export function GovernanceTag({ sourceType }: { sourceType: string }) {
  const { locale, t } = useI18n()
  return (
    <span
      className="governance-tag"
      title={t("This requirement's official source classification, from the versioned knowledge base.")}
    >
      {presentGovernedLabel(sourceType, locale)}
    </span>
  )
}
