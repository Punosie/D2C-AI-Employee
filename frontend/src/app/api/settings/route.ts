import { NextRequest, NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET(req: NextRequest) {
  try {
    const mid  = req.nextUrl.searchParams.get('merchant_id') || 'default'
    const auth = req.headers.get('Authorization') || ''
    const res  = await fetch(`${BACKEND}/settings?merchant_id=${mid}`, {
      headers: auth ? { Authorization: auth } : {},
    })
    if (!res.ok) return NextResponse.json({ error: 'Could not load settings.' }, { status: res.status })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'Could not reach backend.' }, { status: 503 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const auth = req.headers.get('Authorization') || ''
    const res  = await fetch(`${BACKEND}/settings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(auth ? { Authorization: auth } : {}),
      },
      body: JSON.stringify(body),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      return NextResponse.json(
        { saved: false, error: data.error || 'Something went wrong. Please try again.' },
        { status: res.status },
      )
    }
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ saved: false, error: 'Could not reach backend.' }, { status: 503 })
  }
}
