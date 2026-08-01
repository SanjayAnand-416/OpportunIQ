import {
  Calendar,
  Check,
  CheckCircle2,
  Clock,
  Loader2,
  Mail,
  RefreshCw,
  RotateCw,
  Shield,
  Unlink,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { disconnectGmail, getGmailErrorMessage, getGmailStatus, GMAIL_CONNECT_URL, scanGmailInbox } from '../../api/gmail'
import { ROUTES } from '../../constants/routes'
import { formatLastScanned } from '../../utils/gmail'
import ErrorBanner from '../common/ErrorBanner'

const TRUST_POINTS = ['Read-only access', 'We never modify your emails', 'Secure OAuth authentication']

function DisconnectedView({ disabled, onConnect }) {
  return (
    <>
      <span className="gmail-card-icon gmail-card-icon-neutral" aria-hidden="true">
        <Shield size={22} />
      </span>
      <h3 className="gmail-card-title">Connect your Gmail</h3>
      <p className="gmail-card-description">
        Read-only Gmail access allows OpportunIQ to discover interview schedules, application
        deadlines, hackathon submissions, offer acceptance dates and other important events.
      </p>
      <ul className="gmail-trust-list">
        {TRUST_POINTS.map((point) => (
          <li key={point}>
            <Check size={14} aria-hidden="true" />
            {point}
          </li>
        ))}
      </ul>
      <button
        type="button"
        className="gmail-connect-btn"
        onClick={onConnect}
        disabled={disabled}
        aria-label="Connect Gmail account"
      >
        <Mail size={16} aria-hidden="true" />
        Connect Gmail
      </button>
      <Link to={ROUTES.DEADLINES} className="gmail-manual-link">
        I&apos;ll add deadlines manually
      </Link>
    </>
  )
}

function ConnectedView({ gmailStatus, isScanning, isDisconnecting, disabled, onRescan, onDisconnect }) {
  const { email, last_scanned: lastScanned, deadlines_found: deadlinesFound } = gmailStatus

  return (
    <>
      <span className="gmail-card-icon gmail-card-icon-success" aria-hidden="true">
        <CheckCircle2 size={22} />
      </span>
      <h3 className="gmail-card-title">Gmail Connected</h3>

      <dl className="gmail-status-list">
        <div className="gmail-status-row">
          <dt>
            <Mail size={14} aria-hidden="true" />
            Email
          </dt>
          <dd>{email || 'Not available'}</dd>
        </div>
        <div className="gmail-status-row">
          <dt>
            <Clock size={14} aria-hidden="true" />
            Last scan
          </dt>
          <dd>{formatLastScanned(lastScanned)}</dd>
        </div>
        <div className="gmail-status-row">
          <dt>
            <Calendar size={14} aria-hidden="true" />
            Deadlines found
          </dt>
          <dd>{Number.isFinite(deadlinesFound) ? deadlinesFound : 0}</dd>
        </div>
      </dl>

      <div className="gmail-actions">
        <button
          type="button"
          className="gmail-action-btn gmail-action-secondary"
          onClick={onRescan}
          disabled={disabled}
          aria-label="Re-scan Gmail inbox for deadlines"
        >
          {isScanning ? (
            <Loader2 size={15} className="trace-icon-spin" aria-hidden="true" />
          ) : (
            <RefreshCw size={15} aria-hidden="true" />
          )}
          Re-scan Inbox
        </button>
        <button
          type="button"
          className="gmail-action-btn gmail-action-outline"
          onClick={onDisconnect}
          disabled={disabled}
          aria-label="Disconnect Gmail account"
        >
          {isDisconnecting ? (
            <Loader2 size={15} className="trace-icon-spin" aria-hidden="true" />
          ) : (
            <Unlink size={15} aria-hidden="true" />
          )}
          Disconnect
        </button>
      </div>
    </>
  )
}

export default function GmailConnectCard({ profileId }) {
  const [gmailStatus, setGmailStatus] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isScanning, setIsScanning] = useState(false)
  const [isDisconnecting, setIsDisconnecting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const fetchStatus = useCallback(async () => {
    setIsLoading(true)
    setErrorMessage('')
    try {
      const data = await getGmailStatus(profileId)
      setGmailStatus(data)
    } catch (error) {
      setErrorMessage(getGmailErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }, [profileId])

  useEffect(() => {
    Promise.resolve().then(fetchStatus)
  }, [fetchStatus])

  function handleConnectClick() {
    window.location.href = `${GMAIL_CONNECT_URL}?profile_id=${encodeURIComponent(profileId)}`
  }

  async function handleRescan() {
    setIsScanning(true)
    setErrorMessage('')
    try {
      await scanGmailInbox(profileId)
      await fetchStatus()
    } catch (error) {
      setErrorMessage(getGmailErrorMessage(error))
    } finally {
      setIsScanning(false)
    }
  }

  async function handleDisconnect() {
    setIsDisconnecting(true)
    setErrorMessage('')
    try {
      await disconnectGmail(profileId)
      await fetchStatus()
    } catch (error) {
      setErrorMessage(getGmailErrorMessage(error))
    } finally {
      setIsDisconnecting(false)
    }
  }

  const isBusy = isLoading || isScanning || isDisconnecting

  return (
    <section className="gmail-card" aria-label="Gmail integration status">
      {isLoading && !gmailStatus ? (
        <div className="gmail-card-loading">
          <Loader2 size={22} className="trace-icon-spin" aria-hidden="true" />
          <p>Checking Gmail connection...</p>
        </div>
      ) : (
        <>
          {errorMessage && (
            <div className="gmail-error">
              <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
              <button
                type="button"
                className="gmail-retry-btn"
                onClick={fetchStatus}
                aria-label="Retry loading Gmail status"
              >
                <RotateCw size={14} aria-hidden="true" />
                Retry
              </button>
            </div>
          )}

          {gmailStatus &&
            (gmailStatus.connected ? (
              <ConnectedView
                gmailStatus={gmailStatus}
                isScanning={isScanning}
                isDisconnecting={isDisconnecting}
                disabled={isBusy}
                onRescan={handleRescan}
                onDisconnect={handleDisconnect}
              />
            ) : (
              <DisconnectedView disabled={isBusy} onConnect={handleConnectClick} />
            ))}
        </>
      )}
    </section>
  )
}
