import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/metrics`)
    if (!res.ok) return NextResponse.json({ error: `Backend returned ${res.status}` }, { status: res.status })
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ error: 'Could not reach backend' }, { status: 503 })
  }
}
