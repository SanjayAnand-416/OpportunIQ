import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  handleRetry = () => {
    this.setState({ hasError: false })
  }

  handleDashboard = () => {
    window.location.assign('/dashboard')
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children
    }

    return (
      <main className="app-error-boundary" role="alert">
        <section className="app-error-card">
          <span className="app-error-mark" aria-hidden="true">
            !
          </span>
          <h1>Something went wrong</h1>
          <p>
            OpportunIQ recovered safely from an interface error. You can retry
            the current view or return to the dashboard.
          </p>
          <div className="app-error-actions">
            <button type="button" className="ui-btn ui-btn-primary" onClick={this.handleRetry}>
              Retry
            </button>
            <button
              type="button"
              className="ui-btn ui-btn-secondary"
              onClick={this.handleDashboard}
            >
              Return to Dashboard
            </button>
          </div>
        </section>
      </main>
    )
  }
}

