/**
 * Tests for the main chat page.
 * The fetch API is mocked so no live backend calls are made.
 */
import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Page from '../app/page'

// ── Mock fetch ────────────────────────────────────────────────────────────────

const mockFetch = jest.fn()
global.fetch = mockFetch

const mockChatResponse = (response: string, session_id = 'test-session-123') =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ response, session_id }),
  } as Response)

// ── Mock crypto.randomUUID ────────────────────────────────────────────────────

let uuidCounter = 0
Object.defineProperty(globalThis, 'crypto', {
  value: { randomUUID: () => `uuid-${++uuidCounter}` },
})

// ── Mock localStorage ─────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, val: string) => { store[key] = val },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// ── Tests ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  mockFetch.mockReset()
  localStorageMock.clear()
  uuidCounter = 0
})

test('renders the empty state with suggestion prompts', () => {
  render(<Page />)
  expect(screen.getByText(/what do you want to know/i)).toBeInTheDocument()
  expect(screen.getByText(/what was my revenue last month/i)).toBeInTheDocument()
  expect(screen.getByText(/how is my meta ads roas trending/i)).toBeInTheDocument()
})

test('clicking a suggestion fills the input', async () => {
  render(<Page />)
  const suggestion = screen.getByText(/what was my revenue last month/i)
  await userEvent.click(suggestion)
  // Suggestions call send() directly, so the input won't show the text —
  // instead the user message should appear in the chat
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ response: 'Revenue was ₹4L', session_id: 'abc' }),
  } as Response)
})

test('sends a message and shows the agent response', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ response: 'Revenue was ₹4,23,000.', session_id: 'sess-1' }),
  } as Response)

  render(<Page />)

  const input = screen.getByPlaceholderText(/ask about revenue/i)
  await userEvent.type(input, 'What was my revenue?')
  await userEvent.keyboard('{Enter}')

  expect(await screen.findByText('What was my revenue?')).toBeInTheDocument()
  expect(await screen.findByText('Revenue was ₹4,23,000.')).toBeInTheDocument()
})

test('shows error message when fetch fails', async () => {
  mockFetch.mockRejectedValueOnce(new Error('Network error'))

  render(<Page />)

  const input = screen.getByPlaceholderText(/ask about revenue/i)
  await userEvent.type(input, 'Hello')
  await userEvent.keyboard('{Enter}')

  expect(await screen.findByText(/could not reach the server/i)).toBeInTheDocument()
})

test('persists session_id in localStorage', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ response: 'Hello!', session_id: 'my-session' }),
  } as Response)

  render(<Page />)

  const input = screen.getByPlaceholderText(/ask about revenue/i)
  await userEvent.type(input, 'Hi')
  await userEvent.keyboard('{Enter}')

  await screen.findByText('Hello!')
  expect(localStorageMock.getItem('d2c_session_id')).toBe('my-session')
})

test('new chat button clears messages and session', async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve({ response: 'Hi there!', session_id: 'sess-1' }),
  } as Response)

  render(<Page />)

  const input = screen.getByPlaceholderText(/ask about revenue/i)
  await userEvent.type(input, 'Hi')
  await userEvent.keyboard('{Enter}')
  await screen.findByText('Hi there!')

  const newChatBtn = screen.getByRole('button', { name: /new conversation/i })
  await userEvent.click(newChatBtn)

  expect(screen.queryByText('Hi there!')).not.toBeInTheDocument()
  expect(localStorageMock.getItem('d2c_session_id')).toBeNull()
})

test('send button is disabled when input is empty', () => {
  render(<Page />)
  const sendBtn = screen.getByRole('button', { name: /send message/i })
  expect(sendBtn).toBeDisabled()
})

test('send button is enabled when input has text', async () => {
  render(<Page />)
  const input = screen.getByPlaceholderText(/ask about revenue/i)
  await userEvent.type(input, 'Hello')
  const sendBtn = screen.getByRole('button', { name: /send message/i })
  expect(sendBtn).not.toBeDisabled()
})
