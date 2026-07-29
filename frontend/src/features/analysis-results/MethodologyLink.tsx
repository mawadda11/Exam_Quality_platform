import { useI18n } from '../../i18n/I18nProvider'

interface MethodologyLinkProps {
  anchor: string
  label?: string
}

export function MethodologyLink({
  anchor,
  label = 'Learn how this works',
}: MethodologyLinkProps) {
  const { t } = useI18n()
  return (
    <a className="methodology-link" href={`/evaluation-scope#${anchor}`}>
      {t(label)}
    </a>
  )
}
