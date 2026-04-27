import { useEffect, useMemo, useState } from 'react'

const apiBase = import.meta.env.VITE_API_BASE_URL || ''

export default function App() {
  const [path, setPath] = useState(window.location.pathname)

  useEffect(() => {
    const onPopState = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  function navigate(to) {
    if (window.location.pathname !== to) {
      window.history.pushState({}, '', to)
      setPath(to)
    }
  }

  const route = useMemo(() => matchRoute(path), [path])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand" onClick={() => navigate('/campaigns')} role="button" tabIndex={0}>
          adrobot
        </div>
        <nav className="nav">
          <NavLink active={route.page === 'campaigns'} onClick={() => navigate('/campaigns')}>
            Campaigns
          </NavLink>
          <NavLink active={route.page === 'create'} onClick={() => navigate('/create')}>
            Create
          </NavLink>
        </nav>
      </header>

      <main className="page-wrap">
        {route.page === 'create' ? <CreateCampaignPage /> : null}
        {route.page === 'campaigns' ? <CampaignsPage onOpenCampaign={(id) => navigate(`/campaigns/${id}/edit`)} /> : null}
        {route.page === 'editor' ? (
          <CampaignEditorPage campaignId={route.campaignId} onOpenCampaign={(id) => navigate(`/campaigns/${id}/edit`)} />
        ) : null}
        {route.page === 'not-found' ? <NotFoundPage onGoCampaigns={() => navigate('/campaigns')} /> : null}
      </main>
    </div>
  )
}

function matchRoute(pathname) {
  if (pathname === '/' || pathname === '/campaigns' || pathname === '/campaigns/') {
    return { page: 'campaigns' }
  }

  if (pathname === '/create' || pathname === '/create/') {
    return { page: 'create' }
  }

  const editorMatch = pathname.match(/^\/campaigns\/(\d+)\/edit\/?$/)
  if (editorMatch) {
    return { page: 'editor', campaignId: Number(editorMatch[1]) }
  }

  return { page: 'not-found' }
}

function NavLink({ active, children, onClick }) {
  return (
    <button type="button" className={active ? 'nav-link active' : 'nav-link'} onClick={onClick}>
      {children}
    </button>
  )
}

function NotFoundPage({ onGoCampaigns }) {
  return (
    <div className="card">
      <h1>Page not found</h1>
      <button type="button" onClick={onGoCampaigns}>
        Go to campaigns
      </button>
    </div>
  )
}

function CampaignsPage({ onOpenCampaign }) {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function syncFromKT() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/api/editor/campaigns/sync`, { method: 'POST' })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail?.message || 'Failed to sync campaigns')
      }
      setCampaigns(data.campaigns || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    syncFromKT()
  }, [])

  return (
    <section className="card">
      <div className="section-header">
        <div>
          <h1>Campaigns</h1>
          <p className="muted">Synced from KT on load.</p>
        </div>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="table-card">
        <table className="simple-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>ID</th>
              <th>Flows</th>
              <th>Draft flows</th>
              <th>State</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {campaigns.length === 0 ? (
              <tr>
                <td colSpan="6" className="empty-cell">
                  No campaigns cached yet.
                </td>
              </tr>
            ) : (
              campaigns.map((campaign) => (
                <tr key={campaign.kt_campaign_id}>
                  <td>{campaign.name}</td>
                  <td>#{campaign.kt_campaign_id}</td>
                  <td>{campaign.flow_count}</td>
                  <td>{campaign.draft_flow_count}</td>
                  <td>{campaign.state}</td>
                  <td className="actions-cell">
                    <button type="button" onClick={() => onOpenCampaign(campaign.kt_campaign_id)}>
                      Edit
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function CampaignEditorPage({ campaignId, onOpenCampaign }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function loadCampaign() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/api/editor/campaigns/${campaignId}`)
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload?.detail?.message || 'Failed to load campaign')
      }
      setData(payload)
      if (onOpenCampaign) onOpenCampaign(campaignId)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCampaign()
  }, [campaignId])

  async function postCampaignAction(action) {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/api/editor/campaigns/${campaignId}/${action}`, {
        method: 'POST',
      })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload?.detail?.message || 'Failed to update campaign')
      }
      setData(payload)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!data) {
    return (
      <section className="card">
        <h1>Campaign editor</h1>
        <p className="muted">{loading ? 'Loading…' : 'No data yet'}</p>
        {error ? <p className="error">{error}</p> : null}
      </section>
    )
  }

  const hasDraft = data.state === 'draft'

  return (
    <section className="card editor-card">
      <div className="section-header editor-header">
        <div>
          <h1>{data.campaign.name}</h1>
          <div className="meta-row">
            <span className="badge">{data.state}</span>
            <span className="muted">#{data.campaign.kt_campaign_id}</span>
          </div>
        </div>
        <div className="header-actions">
          {hasDraft ? (
            <>
              <button type="button" onClick={() => postCampaignAction('push')} disabled={loading}>
                {loading ? 'Pushing…' : 'Push to KT'}
              </button>
              <button type="button" onClick={() => postCampaignAction('cancel')} disabled={loading}>
                Cancel
              </button>
            </>
          ) : (
            <button type="button" onClick={() => postCampaignAction('fetch')} disabled={loading}>
              {loading ? 'Fetching…' : 'Fetch from KT'}
            </button>
          )}
        </div>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <div className="flow-list">
        {data.flows.length === 0 ? <p className="muted">No flows cached yet. Fetch from KT to load them.</p> : null}
        {data.flows.map((flow) => (
          <FlowEditor
            key={flow.kt_stream_id}
            campaignId={campaignId}
            flow={flow}
            onChanged={loadCampaign}
          />
        ))}
      </div>
    </section>
  )
}

function FlowEditor({ campaignId, flow, onChanged }) {
  const current = flow.current_state || flow.draft_state || flow.main_state || { offers: [] }
  const offers = current.offers || []
  const [busy, setBusy] = useState(false)

  async function action(action, payload = {}) {
    setBusy(true)
    try {
      const response = await fetch(
        `${apiBase}/api/editor/campaigns/${campaignId}/flows/${flow.kt_stream_id}/actions`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, ...payload }),
        },
      )
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail?.message || 'Failed to update flow')
      }
      onChanged()
    } catch (err) {
      alert(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className={flow.has_draft ? 'flow-card draft' : 'flow-card'}>
      <div className="flow-header">
        <div>
          <h2>{flow.name}</h2>
          <div className="meta-row">
            <span className="badge">{flow.state}</span>
            <span className="muted">Stream #{flow.kt_stream_id}</span>
          </div>
        </div>
      </div>

      <div className="offer-picker-wrap">
        <OfferPicker
          onAdd={(offer) => action('add_offer', { offer_id: offer.id, name: offer.name })}
          disabled={busy}
        />
      </div>

      <div className="table-card">
        <table className="simple-table offers-table">
          <thead>
            <tr>
              <th>Offer</th>
              <th>%</th>
              <th>Pin</th>
              <th>Stats</th>
              <th>Trends</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {offers.length === 0 ? (
              <tr>
                <td colSpan="7" className="empty-cell">
                  No offers in this flow yet.
                </td>
              </tr>
            ) : (
              offers.map((offer) => (
                <tr key={offer.offer_id} className={offer.removed ? 'row-removed' : ''}>
                  <td>{offer.name}</td>
                  <td>
                    {offer.share}%
                  </td>
                  <td>
                    <button
                      type="button"
                      onClick={() => action('toggle_pin', { offer_id: offer.offer_id })}
                      disabled={busy || offer.removed}
                    >
                      {offer.pinned ? 'Unpin' : 'Pin'}
                    </button>
                  </td>
                  <td>—</td>
                  <td>—</td>
                  <td>{offer.removed ? 'Removed' : 'Active'}</td>
                  <td className="actions-cell">
                    {offer.removed ? (
                      <button type="button" onClick={() => action('revive_offer', { offer_id: offer.offer_id })} disabled={busy}>
                        Bring back
                      </button>
                    ) : (
                      <button type="button" onClick={() => action('remove_offer', { offer_id: offer.offer_id })} disabled={busy}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </article>
  )
}

function OfferPicker({ onAdd, disabled }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  useEffect(() => {
    const trimmed = query.trim()
    if (!trimmed) {
      setResults([])
      setError('')
      setLoading(false)
      return undefined
    }

    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${apiBase}/api/offers/search?q=${encodeURIComponent(trimmed)}`, {
          signal: controller.signal,
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data?.detail?.message || 'Failed to search offers')
        }
        setResults(data)
      } catch (err) {
        if (err.name !== 'AbortError') {
          setError(err.message)
          setResults([])
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }, 250)

    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [query])

  const showPanel = query.trim() && (!selected || query.trim() !== `${selected.id} — ${selected.name}`)

  function choose(offer) {
    setSelected(offer)
    setQuery(`${offer.id} — ${offer.name}`)
    setResults([])
  }

  async function addSelected() {
    if (!selected) return
    await onAdd(selected)
    setQuery('')
    setSelected(null)
    setResults([])
  }

  return (
    <div className="offer-picker">
      <div className="offer-input-row">
        <input
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setSelected(null)
          }}
          placeholder="Search by offer id or name"
          autoComplete="off"
          inputMode="search"
          disabled={disabled}
        />
        <button type="button" onClick={addSelected} disabled={disabled || !selected}>
          Add
        </button>
      </div>

      {showPanel ? (
        <div className="autocomplete-panel">
          {loading ? <div className="autocomplete-status">Searching…</div> : null}
          {!loading && error ? <div className="autocomplete-status">{error}</div> : null}
          {!loading && !error && results.length === 0 ? <div className="autocomplete-status">No offers found</div> : null}
          {!loading
            ? results.map((offer) => (
                <button key={offer.id} type="button" className="autocomplete-item" onClick={() => choose(offer)}>
                  <span className="autocomplete-id">#{offer.id}</span>
                  <span className="autocomplete-name">{offer.name}</span>
                  {offer.state ? <span className="autocomplete-meta">{offer.state}</span> : null}
                </button>
              ))
            : null}
        </div>
      ) : null}
    </div>
  )
}

function CreateCampaignPage() {
  const [form, setForm] = useState({ name: '', country_code: '', offer_id: '' })
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [offerQuery, setOfferQuery] = useState('')
  const [offerResults, setOfferResults] = useState([])
  const [offerLoading, setOfferLoading] = useState(false)
  const [offerError, setOfferError] = useState('')
  const [selectedOffer, setSelectedOffer] = useState(null)

  useEffect(() => {
    fetch(`${apiBase}/api/config`)
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data?.detail?.message || 'Failed to load config')
        setConfig(data)
      })
      .catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    const query = offerQuery.trim()
    if (!query) {
      setOfferResults([])
      setOfferError('')
      setOfferLoading(false)
      return undefined
    }

    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setOfferLoading(true)
      setOfferError('')
      try {
        const response = await fetch(`${apiBase}/api/offers/search?q=${encodeURIComponent(query)}`, {
          signal: controller.signal,
        })
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data?.detail?.message || 'Failed to search offers')
        }
        setOfferResults(data)
      } catch (err) {
        if (err.name !== 'AbortError') {
          setOfferError(err.message)
          setOfferResults([])
        }
      } finally {
        if (!controller.signal.aborted) {
          setOfferLoading(false)
        }
      }
    }, 250)

    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [offerQuery])

  const selectedOfferLabel = selectedOffer ? `${selectedOffer.id} — ${selectedOffer.name}` : ''
  const showOfferPanel = offerQuery.trim() && offerQuery.trim() !== selectedOfferLabel

  const canSubmit = useMemo(() => {
    return form.name.trim() && form.country_code.trim() && Number(form.offer_id) > 0 && !loading
  }, [form, loading])

  function chooseOffer(offer) {
    setSelectedOffer(offer)
    setOfferQuery(`${offer.id} — ${offer.name}`)
    setForm((prev) => ({ ...prev, offer_id: String(offer.id) }))
    setOfferResults([])
  }

  async function onSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setMessage('')
    setError('')
    setResult(null)

    try {
      const response = await fetch(`${apiBase}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name,
          country_code: form.country_code,
          offer_id: Number(form.offer_id),
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data?.detail?.message || 'Failed to create campaign')
      }
      setResult(data)
      setMessage('Campaign created successfully.')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="card">
      <div className="section-header">
        <div>
          <h1>Create a campaign</h1>
        </div>
      </div>

      <section className="config-box">
        <h2>Resolved Keitaro config</h2>
        {config ? (
          <div className="config-grid">
            <ConfigItem label="Domain" value={config.domain ? `${config.domain.name} (#${config.domain.id})` : '—'} />
            <ConfigItem label="Group" value={config.group ? `${config.group.name} (#${config.group.id})` : '—'} />
            <ConfigItem label="Traffic source" value={config.traffic_source ? `${config.traffic_source.name} (#${config.traffic_source.id})` : '—'} />
          </div>
        ) : (
          <p className="muted">Loading config…</p>
        )}
      </section>

      <form onSubmit={onSubmit} className="form">
        <label>
          Campaign name
          <input
            value={form.name}
            onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
            placeholder="My GEO campaign"
          />
        </label>

        <label>
          Country geo code
          <input
            value={form.country_code}
            onChange={(e) => setForm((prev) => ({ ...prev, country_code: e.target.value.toUpperCase() }))}
            placeholder="AU"
            maxLength={8}
          />
        </label>

        <label className="offer-field">
          Offer
          <div className="autocomplete">
            <input
              value={offerQuery}
              onChange={(e) => {
                setOfferQuery(e.target.value)
                setSelectedOffer(null)
                setForm((prev) => ({ ...prev, offer_id: e.target.value.replace(/[^0-9]/g, '') }))
              }}
              placeholder="Search by offer id or name"
              autoComplete="off"
              inputMode="search"
            />
            {showOfferPanel ? (
              <div className="autocomplete-panel">
                {offerLoading ? <div className="autocomplete-status">Searching offers…</div> : null}
                {!offerLoading && offerError ? <div className="autocomplete-status">{offerError}</div> : null}
                {!offerLoading && !offerError && offerResults.length === 0 ? (
                  <div className="autocomplete-status">No offers found</div>
                ) : null}
                {!offerLoading
                  ? offerResults.map((offer) => (
                      <button
                        key={offer.id}
                        type="button"
                        className="autocomplete-item"
                        onClick={() => chooseOffer(offer)}
                      >
                        <span className="autocomplete-id">#{offer.id}</span>
                        <span className="autocomplete-name">{offer.name}</span>
                        {offer.state ? <span className="autocomplete-meta">{offer.state}</span> : null}
                      </button>
                    ))
                  : null}
              </div>
            ) : null}
          </div>
        </label>

        <button type="submit" disabled={!canSubmit}>
          {loading ? 'Creating…' : 'Create campaign'}
        </button>
      </form>

      {message ? <p className="success">{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <section className="result">
          <h2>Created campaign</h2>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </section>
      ) : null}
    </section>
  )
}

function ConfigItem({ label, value }) {
  return (
    <div className="config-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}
