export default function StepIndicator({ steps, activeStep }) {
  return (
    <nav className="step-indicator" aria-label="Onboarding progress">
      {steps.map((step, index) => {
        const stepNumber = index + 1
        const isActive = stepNumber === activeStep
        const isComplete = stepNumber < activeStep

        return (
          <div className="step-item" key={step.label}>
            <div
              className={`step-marker ${
                isActive || isComplete ? 'step-marker-active' : ''
              }`}
              aria-current={isActive ? 'step' : undefined}
            >
              {stepNumber}
            </div>
            <div>
              <p className="step-count">Step {stepNumber}</p>
              <p
                className={`step-label ${
                  isActive ? 'step-label-active' : ''
                }`}
              >
                {step.label}
              </p>
            </div>
            {index < steps.length - 1 && (
              <div
                className={`step-line ${
                  isComplete ? 'step-line-active' : ''
                }`}
                aria-hidden="true"
              />
            )}
          </div>
        )
      })}
    </nav>
  )
}
