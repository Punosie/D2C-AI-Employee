'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, Plus, Zap, Loader2, RotateCcw, Settings, LogOut, AlertTriangle } from 'lucide-react'
import { createClient } from '@/lib/supabase'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  id: string
  role: 'user' | 'agent'
  content: string
  error?: boolean
}

// ── Suggested prompts ─────────────────────────────────────────────────────────

const SUGGESTIONS = [
  'What was my revenue last month?',
  'How is my Meta Ads ROAS trending?',
  'Which products are running low on stock?',
  "What's my repeat customer rate?",
]

// ── Citation extraction ───────────────────────────────────────────────────────

interface CitationRef {
  index: number
  connector: string
  table: string
  id: string
}

const CONNECTOR_LABELS: Record<string, string> = {
  shopify:       'Shopify',
  meta_ads:      'Meta Ads',
  google_sheets: 'Google Sheets',
  source:        'Data',
}

function extractCitations(text: string): { body: string; refs: CitationRef[] } {
  const seen = new Map<string, number>()
  const refs: CitationRef[] = []
  let counter = 1

  // Match [connector:table#id] — connector is any lowercase word, id may be empty
  const body = text.replace(
    /\[([a-z_]+):([a-z_]+)#([^\]]*)\]/g,
    (_match, connector, table, id) => {
      const key = `${connector}:${table}#${id}`
      if (!seen.has(key)) {
        seen.set(key, counter)
        refs.push({ index: counter, connector, table, id: id.trim() })
        counter++
      }
      return `[${seen.get(key)}]`
    }
  )
  return { body, refs }
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const router   = useRouter()
  const supabase = createClient()

  const [messages, setMessages]       = useState<Message[]>([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [sessionId, setSessionId]     = useState('')
  const [merchantId, setMerchantId]   = useState('')
  const [authToken, setAuthToken]     = useState('')
  const [userEmail, setUserEmail]     = useState('')
  const [connectorStatus, setConnectorStatus] = useState<Record<string, { configured: boolean }>>({})
  const [statusLoaded, setStatusLoaded] = useState(false)
  const bottomRef   = useRef<HTMLDivElement>(null)
  const inputRef    = useRef<HTMLTextAreaElement>(null)
  const messagesRef = useRef<HTMLDivElement>(null)

  const hasConnectors = Object.values(connectorStatus).some((v) => v.configured)

  const fetchConnectorStatus = useCallback((mid: string, token: string) => {
    fetch(`/api/settings?merchant_id=${mid}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((data) => { setConnectorStatus(data); setStatusLoaded(true) })
      .catch(() => setStatusLoaded(true))
  }, [])

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!session) { router.push('/login'); return }
      setMerchantId(session.user.id)
      setAuthToken(session.access_token)
      setUserEmail(session.user.email ?? '')
      setSessionId(localStorage.getItem('d2c_session_id') || '')
      fetchConnectorStatus(session.user.id, session.access_token)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) { router.push('/login'); return }
      setMerchantId(session.user.id)
      setAuthToken(session.access_token)
      setUserEmail(session.user.email ?? '')
    })

    return () => subscription.unsubscribe()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const signOut = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  const newChat = () => {
    localStorage.removeItem('d2c_session_id')
    setSessionId('')
    setMessages([])
    inputRef.current?.focus()
  }

  const send = useCallback(
    async (text?: string) => {
      const msg = (text ?? input).trim()
      if (!msg || loading) return

      setInput('')
      setLoading(true)
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: msg },
      ])

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
          },
          body: JSON.stringify({ message: msg, session_id: sessionId, merchant_id: merchantId }),
        })
        const data = await res.json()

        if (data.session_id) {
          setSessionId(data.session_id)
          localStorage.setItem('d2c_session_id', data.session_id)
        }

        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'agent',
            content: data.error ?? data.response ?? 'No response.',
            error: !!data.error,
          },
        ])
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'agent',
            content: 'Could not reach the server. Is the backend running?',
            error: true,
          },
        ])
      } finally {
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 0)
      }
    },
    [input, loading, sessionId, merchantId, authToken]
  )

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!hasConnectors) return
      send()
    }
  }

  const autoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  const inputDisabled = loading || (statusLoaded && !hasConnectors)
  const inputPlaceholder = statusLoaded && !hasConnectors
    ? 'Connect a data source in Settings to start chatting…'
    : 'Ask about revenue, ROAS, inventory…'

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Sidebar */}
      <aside className="hidden md:flex flex-col w-60 bg-gray-900 text-white shrink-0">
        <div className="flex items-center gap-2.5 px-4 py-5 border-b border-white/10">
          <div className="w-7 h-7 bg-white rounded-lg flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4 text-gray-900" />
          </div>
          <span className="font-semibold text-sm">D2C AI Employee</span>
        </div>

        <div className="flex-1 p-3">
          <button
            onClick={newChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-300 hover:bg-white/10 hover:text-white transition-colors"
          >
            <Plus className="w-4 h-4" />
            New conversation
          </button>
        </div>

        <div className="p-4 border-t border-white/10">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-500">Data sources</p>
            <Link href="/settings" className="text-gray-500 hover:text-white transition-colors" title="Connector settings">
              <Settings className="w-3.5 h-3.5" />
            </Link>
          </div>
          <ConnectorDots status={connectorStatus} />
          {userEmail && (
            <div className="mt-3 pt-3 border-t border-white/10">
              <p className="text-xs text-gray-500 truncate mb-1.5">{userEmail}</p>
              <button
                onClick={signOut}
                className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
              >
                <LogOut className="w-3 h-3" /> Sign out
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Mobile header */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4" />
            <span className="font-semibold text-sm">D2C AI Employee</span>
          </div>
          <button onClick={newChat} className="text-gray-500 hover:text-gray-900">
            <RotateCcw className="w-4 h-4" />
          </button>
        </header>

        {/* No-connector warning banner */}
        {statusLoaded && !hasConnectors && (
          <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 flex items-center gap-2 text-sm text-amber-800">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>
              No data sources connected.{' '}
              <Link href="/settings" className="font-semibold underline hover:text-amber-900">
                Go to Settings
              </Link>{' '}
              to connect Shopify, Meta Ads, or Google Sheets.
            </span>
          </div>
        )}

        {/* Messages */}
        <div ref={messagesRef} className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-4 py-8 flex flex-col gap-6">
            {messages.length === 0 ? (
              <EmptyState hasConnectors={hasConnectors} statusLoaded={statusLoaded} onSuggest={(s) => send(s)} />
            ) : (
              messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
            )}

            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-gray-200 bg-white px-4 py-4">
          <div className="max-w-2xl mx-auto flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={autoResize}
              onKeyDown={handleKeyDown}
              placeholder={inputPlaceholder}
              rows={1}
              disabled={inputDisabled}
              className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-3 text-sm outline-none focus:border-gray-400 disabled:bg-gray-50 disabled:text-gray-400 transition-colors leading-relaxed"
              style={{ minHeight: '44px', maxHeight: '160px' }}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading || !hasConnectors}
              aria-label="Send message"
              className="shrink-0 p-3 bg-gray-900 text-white rounded-xl hover:bg-gray-700 disabled:bg-gray-200 disabled:text-gray-400 transition-colors"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="max-w-2xl mx-auto text-center text-xs text-gray-400 mt-2">
            {hasConnectors ? 'Enter to send · Shift+Enter for new line' : 'Connect a data source above to enable chat'}
          </p>
        </div>
      </div>
    </div>
  )
}

// ── ConnectorDots ─────────────────────────────────────────────────────────────

function ConnectorDots({ status }: { status: Record<string, { configured: boolean }> }) {
  const connectors = [
    { key: 'shopify',       label: 'Shopify' },
    { key: 'meta_ads',      label: 'Meta Ads' },
    { key: 'google_sheets', label: 'Google Sheets' },
  ]

  return (
    <div className="flex flex-col gap-1.5">
      {connectors.map(({ key, label }) => (
        <div key={key} className="flex items-center gap-2 text-xs text-gray-400">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${status[key]?.configured ? 'bg-emerald-400' : 'bg-gray-600'}`} />
          {label}
        </div>
      ))}
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-gray-900 text-white rounded-2xl rounded-br-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start gap-3">
      <div className="shrink-0 w-7 h-7 bg-gray-100 rounded-full flex items-center justify-center mt-0.5">
        <Zap className="w-3.5 h-3.5 text-gray-600" />
      </div>
      <div
        className={`max-w-[85%] rounded-2xl rounded-bl-sm px-4 py-3 text-sm leading-relaxed shadow-sm border ${
          message.error
            ? 'bg-red-50 border-red-100 text-red-700'
            : 'bg-white border-gray-100 text-gray-800'
        }`}
      >
        <CitedContent text={message.content} />
      </div>
    </div>
  )
}

// ── CitedContent — Perplexity-style inline badges + Sources panel ─────────────

function CitedContent({ text }: { text: string }) {
  const { body, refs } = extractCitations(text)
  const parts = body.split(/(\[\d+\])/)

  return (
    <div>
      <div className="prose prose-sm leading-relaxed">
        {parts.map((part, i) => {
          const m = part.match(/^\[(\d+)\]$/)
          if (m) {
            return (
              <sup
                key={i}
                title={`Source ${m[1]}`}
                className="inline-flex items-center justify-center min-w-[15px] h-[15px] px-0.5 rounded bg-blue-100 text-blue-700 font-bold text-[9px] mx-0.5 not-italic cursor-default select-none"
              >
                {m[1]}
              </sup>
            )
          }
          if (!part) return null
          return (
            <ReactMarkdown
              key={i}
              remarkPlugins={[remarkGfm]}
              components={{ p: ({ children }) => <span>{children}</span> }}
            >
              {part}
            </ReactMarkdown>
          )
        })}
      </div>

      {refs.length > 0 && (
        <div className="mt-3 pt-2.5 border-t border-gray-100">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">
            Sources
          </p>
          <div className="flex flex-col gap-1">
            {refs.map((ref) => (
              <div key={ref.index} className="flex items-center gap-2 text-xs">
                <span className="inline-flex items-center justify-center min-w-[16px] h-4 px-1 rounded bg-blue-100 text-blue-700 font-bold text-[9px] shrink-0">
                  {ref.index}
                </span>
                <span className="font-medium text-gray-700">
                  {CONNECTOR_LABELS[ref.connector] ?? ref.connector}
                </span>
                <span className="text-gray-300">·</span>
                <span className="font-mono text-[11px] text-gray-500">
                  {ref.table}{ref.id ? ` #${ref.id}` : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex justify-start gap-3">
      <div className="shrink-0 w-7 h-7 bg-gray-100 rounded-full flex items-center justify-center">
        <Zap className="w-3.5 h-3.5 text-gray-600" />
      </div>
      <div className="bg-white rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-gray-100">
        <div className="flex gap-1 items-center h-4">
          {['-0.3s', '-0.15s', '0s'].map((delay) => (
            <span
              key={delay}
              className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
              style={{ animationDelay: delay }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function EmptyState({
  hasConnectors,
  statusLoaded,
  onSuggest,
}: {
  hasConnectors: boolean
  statusLoaded: boolean
  onSuggest: (s: string) => void
}) {
  if (statusLoaded && !hasConnectors) {
    return (
      <div className="flex flex-col items-center text-center py-16">
        <div className="w-14 h-14 bg-amber-100 rounded-2xl flex items-center justify-center mb-5">
          <AlertTriangle className="w-7 h-7 text-amber-600" />
        </div>
        <h1 className="text-xl font-semibold text-gray-900 mb-2">
          No data sources connected
        </h1>
        <p className="text-sm text-gray-500 mb-6 max-w-sm">
          Connect Shopify, Meta Ads, or Google Sheets so your AI employee has data to work with.
        </p>
        <Link
          href="/settings"
          className="px-5 py-2.5 bg-gray-900 text-white text-sm font-medium rounded-xl hover:bg-gray-700 transition-colors"
        >
          Go to Settings
        </Link>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center text-center py-16">
      <div className="w-14 h-14 bg-gray-900 rounded-2xl flex items-center justify-center mb-5">
        <Zap className="w-7 h-7 text-white" />
      </div>
      <h1 className="text-xl font-semibold text-gray-900 mb-2">
        What do you want to know?
      </h1>
      <p className="text-sm text-gray-500 mb-10 max-w-sm">
        Ask anything about your revenue, ad spend, inventory, or customers.
        Every answer is cited back to the source data.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggest(s)}
            className="text-left text-sm text-gray-700 bg-white border border-gray-200 rounded-xl px-4 py-3.5 hover:border-gray-400 hover:shadow-sm transition-all"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
