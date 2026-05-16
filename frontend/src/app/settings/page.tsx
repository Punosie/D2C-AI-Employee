'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  Zap, ChevronLeft, CheckCircle2, XCircle, Info,
  Copy, Check, ChevronDown, ChevronUp, Eye, EyeOff,
  ExternalLink, AlertTriangle, RefreshCw, Loader2,
} from 'lucide-react'
import { createClient } from '@/lib/supabase'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Status {
  shopify:       { configured: boolean; store_url: string }
  meta_ads:      { configured: boolean; account_id: string }
  google_sheets: { configured: boolean; sheet_ids: string }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const router   = useRouter()
  const supabase = createClient()

  const [status, setStatus]           = useState<Status | null>(null)
  const [googleEmail, setGoogleEmail] = useState<string | null>(null)
  const [merchantId, setMerchantId]   = useState('default')
  const [authToken, setAuthToken]     = useState('')
  const [syncing, setSyncing]         = useState(false)
  const [toast, setToast]             = useState<string | null>(null)
  const [lastSyncAt, setLastSyncAt]   = useState<number | null>(null)

  const handleSync = async () => {
    if (syncing) return
    if (lastSyncAt && Date.now() - lastSyncAt < 2 * 60 * 1000) {
      setToast('Already synced')
      return
    }
    setSyncing(true)
    try {
      await fetch('/api/sync', { method: 'POST', headers: authToken ? { Authorization: `Bearer ${authToken}` } : {} })
      setLastSyncAt(Date.now())
      setToast('Sync complete')
    } catch {
      setToast('Sync failed — try again')
    } finally {
      setSyncing(false)
    }
  }

  const load = useCallback((mid: string, token: string) => {
    fetch(`/api/settings?merchant_id=${mid}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.json()).then(setStatus).catch(() => {})
    fetch('/api/settings/google-email')
      .then(r => r.json()).then(d => setGoogleEmail(d.email || null)).catch(() => {})
  }, [])

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.push('/login'); return }
      setMerchantId(session.user.id)
      setAuthToken(session.access_token)
      load(session.user.id, session.access_token)
    })
  }, [load])

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-60 bg-slate-950 text-white shrink-0">
        <div className="flex items-center gap-2.5 px-4 py-5 border-b border-white/10">
          <div className="w-7 h-7 bg-white rounded-lg flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4 text-slate-900" />
          </div>
          <span className="font-semibold text-sm">D2C AI Employee</span>
        </div>
        <div className="flex-1 p-3">
          <Link href="/" className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-white/10 hover:text-white transition-colors">
            <ChevronLeft className="w-4 h-4" /> Back to chat
          </Link>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-xl mx-auto px-4 py-10">

          <div className="mb-8 flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Connect your data</h1>
              <p className="text-sm text-slate-500 mt-1">
                Connect the tools you use to run your business. Your AI employee will read live data from them.
              </p>
            </div>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="shrink-0 mt-1 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-slate-900 text-white rounded-xl hover:bg-slate-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors"
            >
              {syncing
                ? <><Loader2 className="w-4 h-4 animate-spin" /> Syncing…</>
                : <><RefreshCw className="w-4 h-4" /> Sync now</>}
            </button>
          </div>

          {status && !Object.values(status).some((v) => v.configured) && (
            <div className="mb-6 flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3.5">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <p className="text-sm text-amber-800">
                No data sources connected yet. Connect at least one below to start chatting with your AI employee.
              </p>
            </div>
          )}

          <div className="flex flex-col gap-4">
            <ShopifyCard
              configured={status?.shopify.configured ?? false}
              prefillStore={status?.shopify.store_url ?? ''}
              merchantId={merchantId}
              authToken={authToken}
              onSaved={() => load(merchantId, authToken)}
            />
            <MetaCard
              configured={status?.meta_ads.configured ?? false}
              prefillAccountId={status?.meta_ads.account_id ?? ''}
              merchantId={merchantId}
              authToken={authToken}
              onSaved={() => load(merchantId, authToken)}
            />
            <GoogleSheetsCard
              configured={status?.google_sheets.configured ?? false}
              prefillSheetIds={status?.google_sheets.sheet_ids ?? ''}
              serviceEmail={googleEmail}
              merchantId={merchantId}
              authToken={authToken}
              onSaved={() => load(merchantId, authToken)}
            />
          </div>

          <p className="text-center text-xs text-slate-400 mt-8">
            Your credentials are encrypted and stored securely. We never share them.
          </p>
        </div>
      </div>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}
    </div>
  )
}

// ── Shared pieces ─────────────────────────────────────────────────────────────

function StatusBadge({ configured }: { configured: boolean }) {
  return configured ? (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
      <CheckCircle2 className="w-3 h-3" /> Connected
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full">
      <XCircle className="w-3 h-3" /> Not connected
    </span>
  )
}

function GuideToggle({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-3 rounded-xl border border-blue-100 bg-blue-50 overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 text-xs font-medium text-blue-700 hover:bg-blue-100 transition-colors"
      >
        <span className="flex items-center gap-1.5"><Info className="w-3.5 h-3.5" /> How to find these details</span>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
      </button>
      {open && <div className="px-4 pb-4 text-xs text-blue-800 leading-relaxed">{children}</div>}
    </div>
  )
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <div className="flex gap-2 mt-2">
      <span className="shrink-0 w-5 h-5 rounded-full bg-blue-200 text-blue-800 font-bold text-[10px] flex items-center justify-center">{n}</span>
      <span>{children}</span>
    </div>
  )
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="ml-1 inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors">
      {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
    </button>
  )
}

function SecretInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 transition-all pr-10"
      />
      <button type="button" onClick={() => setShow(s => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
    </div>
  )
}

function ConnectButton({ saving, saved, error, disabled }: { saving: boolean; saved: boolean; error: string | null; disabled: boolean }) {
  if (saved) return <div className="flex items-center gap-2 text-sm font-medium text-emerald-700"><CheckCircle2 className="w-4 h-4" /> Connected!</div>
  return (
    <div>
      <button
        disabled={disabled || saving}
        className="px-5 py-2.5 bg-slate-900 text-white text-sm font-medium rounded-xl hover:bg-slate-700 disabled:bg-slate-200 disabled:text-slate-400 transition-colors"
      >
        {saving ? 'Connecting…' : 'Connect'}
      </button>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}

// ── Shopify card ──────────────────────────────────────────────────────────────

function ShopifyCard({ configured, prefillStore, merchantId, authToken, onSaved }: {
  configured: boolean; prefillStore: string; merchantId: string; authToken: string; onSaved: () => void
}) {
  const [open, setOpen]       = useState(!configured)
  const [store, setStore]     = useState(prefillStore)
  const [token, setToken]     = useState('')
  const [saving, setSaving]   = useState(false)
  const [saved, setSaved]     = useState(false)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => { setStore(prefillStore) }, [prefillStore])

  const save = async () => {
    if (!store.trim() || !token.trim()) return
    setSaving(true); setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) },
        body: JSON.stringify({ merchant_id: merchantId, shopify: { store_url: store, api_key: token } }),
      })
      const data = await res.json()
      if (!res.ok || !data.saved) throw new Error(data.error || 'Failed to save')
      setSaved(true); onSaved()
      setTimeout(() => { setSaved(false); setOpen(false) }, 2000)
    } catch (e: any) { setError(e.message || 'Something went wrong.') }
    finally { setSaving(false) }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-[#96bf48]/10 rounded-xl flex items-center justify-center text-lg">🛍️</div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-900">Shopify</span>
              <StatusBadge configured={configured} />
            </div>
            <p className="text-xs text-slate-500">Orders, customers, and inventory</p>
          </div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-100">
          <GuideToggle>
            <Step n={1}>Go to your <a href="https://admin.shopify.com" target="_blank" rel="noreferrer" className="underline inline-flex items-center gap-0.5">Shopify admin <ExternalLink className="w-3 h-3" /></a></Step>
            <Step n={2}>Click <strong>Settings</strong> → <strong>Apps and sales channels</strong></Step>
            <Step n={3}>Click <strong>Develop apps</strong> → <strong>Create an app</strong></Step>
            <Step n={4}>Under <strong>Admin API integration</strong>, select: <em>read_orders, read_customers, read_products</em></Step>
            <Step n={5}>Click <strong>Save</strong> → <strong>Install app</strong></Step>
            <Step n={6}>Copy the <strong>Admin API access token</strong> — paste it below</Step>
          </GuideToggle>

          <div className="mt-4 flex flex-col gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Your store name</label>
              <input
                type="text" value={store} onChange={e => setStore(e.target.value)}
                placeholder="yourstore.myshopify.com"
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 transition-all"
              />
              <p className="mt-1 text-xs text-slate-400">Just the domain — we'll handle the rest</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">API token</label>
              <SecretInput value={token} onChange={setToken} placeholder={configured ? '••••••••' : 'Paste your Admin API access token'} />
              {configured && !token && <p className="mt-1 text-xs text-slate-400">Token saved — paste a new one to replace</p>}
            </div>
            <form onSubmit={e => { e.preventDefault(); save() }}>
              <ConnectButton saving={saving} saved={saved} error={error} disabled={!store.trim() || !token.trim()} />
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Meta Ads card ─────────────────────────────────────────────────────────────

function MetaCard({ configured, prefillAccountId, merchantId, authToken, onSaved }: {
  configured: boolean; prefillAccountId: string; merchantId: string; authToken: string; onSaved: () => void
}) {
  const [open, setOpen]         = useState(!configured)
  const [accountId, setAccountId] = useState(prefillAccountId)
  const [token, setToken]       = useState('')
  const [saving, setSaving]     = useState(false)
  const [saved, setSaved]       = useState(false)
  const [error, setError]       = useState<string | null>(null)

  useEffect(() => { setAccountId(prefillAccountId) }, [prefillAccountId])

  const save = async () => {
    if (!accountId.trim() || !token.trim()) return
    setSaving(true); setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) },
        body: JSON.stringify({ merchant_id: merchantId, meta_ads: { access_token: token, account_id: accountId } }),
      })
      const data = await res.json()
      if (!res.ok || !data.saved) throw new Error(data.error || 'Failed to save')
      setSaved(true); onSaved()
      setTimeout(() => { setSaved(false); setOpen(false) }, 2000)
    } catch (e: any) { setError(e.message || 'Something went wrong.') }
    finally { setSaving(false) }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center text-lg">📊</div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-900">Meta Ads</span>
              <StatusBadge configured={configured} />
            </div>
            <p className="text-xs text-slate-500">Ad spend, ROAS, and campaign data</p>
          </div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-100">
          <GuideToggle>
            <Step n={1}>Go to <a href="https://adsmanager.facebook.com" target="_blank" rel="noreferrer" className="underline inline-flex items-center gap-0.5">Meta Ads Manager <ExternalLink className="w-3 h-3" /></a></Step>
            <Step n={2}>Your <strong>Ad Account ID</strong> is the number at the top (e.g. 123456789)</Step>
            <Step n={3}>For the access token, go to <a href="https://developers.facebook.com/tools/explorer" target="_blank" rel="noreferrer" className="underline inline-flex items-center gap-0.5">Graph API Explorer <ExternalLink className="w-3 h-3" /></a></Step>
            <Step n={4}>Select your app → click <strong>Generate Access Token</strong></Step>
            <Step n={5}>Add permissions: <em>ads_read, ads_management</em> → generate and copy</Step>
          </GuideToggle>

          <div className="mt-4 flex flex-col gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Ad Account ID</label>
              <input
                type="text" value={accountId} onChange={e => setAccountId(e.target.value)}
                placeholder="123456789"
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 transition-all"
              />
              <p className="mt-1 text-xs text-slate-400">Just the number — no "act_" needed</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">Access token</label>
              <SecretInput value={token} onChange={setToken} placeholder={configured ? '••••••••' : 'EAAxxxxxxxxxxxxx'} />
              {configured && !token && <p className="mt-1 text-xs text-slate-400">Token saved — paste a new one to replace</p>}
            </div>
            <form onSubmit={e => { e.preventDefault(); save() }}>
              <ConnectButton saving={saving} saved={saved} error={error} disabled={!accountId.trim() || !token.trim()} />
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Google Sheets card ────────────────────────────────────────────────────────

function GoogleSheetsCard({ configured, prefillSheetIds, serviceEmail, merchantId, authToken, onSaved }: {
  configured: boolean; prefillSheetIds: string; serviceEmail: string | null; merchantId: string; authToken: string; onSaved: () => void
}) {
  const [open, setOpen]         = useState(!configured)
  const [sheetUrl, setSheetUrl] = useState(prefillSheetIds)
  const [saving, setSaving]     = useState(false)
  const [saved, setSaved]       = useState(false)
  const [error, setError]       = useState<string | null>(null)

  useEffect(() => { setSheetUrl(prefillSheetIds) }, [prefillSheetIds])

  const save = async () => {
    if (!sheetUrl.trim()) return
    setSaving(true); setError(null)
    try {
      const res = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}) },
        body: JSON.stringify({ merchant_id: merchantId, google_sheets: { sheet_ids: sheetUrl } }),
      })
      const data = await res.json()
      if (!res.ok || !data.saved) throw new Error(data.error || 'Failed to save')
      setSaved(true); onSaved()
      setTimeout(() => { setSaved(false); setOpen(false) }, 2000)
    } catch (e: any) { setError(e.message || 'Something went wrong.') }
    finally { setSaving(false) }
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      <button onClick={() => setOpen(o => !o)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-green-50 rounded-xl flex items-center justify-center text-lg">📋</div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-900">Google Sheets</span>
              <StatusBadge configured={configured} />
            </div>
            <p className="text-xs text-slate-500">Inventory, budgets, and vendor data</p>
          </div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-slate-100">
          {/* Service email step */}
          <div className="mt-4 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <p className="text-xs font-semibold text-slate-700 mb-1">Step 1 — Share your sheet</p>
            <p className="text-xs text-slate-500 mb-2">
              Open your Google Sheet → click <strong>Share</strong> → invite this email address as <strong>Editor</strong>:
            </p>
            {serviceEmail ? (
              <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2">
                <code className="text-xs text-slate-700 flex-1 break-all">{serviceEmail}</code>
                <CopyButton text={serviceEmail} />
              </div>
            ) : (
              <p className="text-xs text-amber-700 bg-amber-50 px-3 py-2 rounded-lg border border-amber-200">
                Google service account not configured in the backend. Contact your setup person.
              </p>
            )}
          </div>

          <div className="mt-3 p-4 rounded-xl bg-slate-50 border border-slate-200">
            <p className="text-xs font-semibold text-slate-700 mb-2">Step 2 — Paste the sheet link</p>
            <input
              type="text" value={sheetUrl} onChange={e => setSheetUrl(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/..."
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-slate-400 focus:ring-2 focus:ring-slate-100 transition-all"
            />
            <p className="mt-1 text-xs text-slate-400">Paste the full URL — we'll extract the ID automatically</p>
          </div>

          <GuideToggle>
            <Step n={1}>Open your spreadsheet at <a href="https://sheets.google.com" target="_blank" rel="noreferrer" className="underline inline-flex items-center gap-0.5">sheets.google.com <ExternalLink className="w-3 h-3" /></a></Step>
            <Step n={2}>Click the green <strong>Share</strong> button (top right)</Step>
            <Step n={3}>In the "Add people" box, paste the email above and set role to <strong>Editor</strong></Step>
            <Step n={4}>Click <strong>Send</strong> → then come back here and paste the sheet link above</Step>
            <div className="mt-2 pt-2 border-t border-blue-100 text-blue-700 font-medium">Your sheet must have tabs named: <em>Inventory, Raw Material Cost, Vendors, Monthly Budget</em></div>
          </GuideToggle>

          <div className="mt-3">
            <form onSubmit={e => { e.preventDefault(); save() }}>
              <ConnectButton saving={saving} saved={saved} error={error} disabled={!sheetUrl.trim()} />
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000)
    return () => clearTimeout(t)
  }, [onDone])
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 bg-slate-900 text-white text-sm font-medium rounded-xl shadow-lg">
      {message}
    </div>
  )
}
