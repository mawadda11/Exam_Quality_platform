import { useId } from 'react'
import { Icon } from '../../components/ui/Icon'
import { useI18n } from '../../i18n/I18nProvider'
import type { QuestionFilterValues } from './questionPresentation'

interface QuestionFiltersProps {
  values: QuestionFilterValues
  resultCount: number
  totalCount: number
  onChange: (values: QuestionFilterValues) => void
}

export function QuestionFilters({
  values,
  resultCount,
  totalCount,
  onChange,
}: QuestionFiltersProps) {
  const { t } = useI18n()
  const id = useId()

  return (
    <div className="question-filters" aria-label={t('Filter questions')}>
      <div className="question-filter-fields">
        <label className="question-search-field" htmlFor={`${id}-search`}>
          <span>{t('Search questions')}</span>
          <span className="question-search-input">
            <Icon name="search" className="ui-icon--sm" />
            <input
              id={`${id}-search`}
              type="search"
              value={values.search}
              placeholder={t('Search by question ID or text')}
              onChange={(event) => onChange({ ...values, search: event.target.value })}
            />
          </span>
        </label>
      </div>
      <div className="question-filter-summary">
        <span role="status">
          {t('Showing {shown} of {total} questions', {
            shown: resultCount,
            total: totalCount,
          })}
        </span>
      </div>
    </div>
  )
}
