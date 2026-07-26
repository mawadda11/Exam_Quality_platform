import { Link } from 'react-router-dom'
import { PageState } from '../components/ui/PageState'

export function NotFoundRoute() {
  return (
    <div className="route-content-compact">
      <PageState
        state="error"
        title="Page not found"
        message="This application route does not exist."
        action={
          <Link className="ui-button ui-button--secondary" to="/dashboard">
            Return to Dashboard
          </Link>
        }
      />
    </div>
  )
}
