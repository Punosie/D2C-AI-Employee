import { NextResponse } from 'next/server'

const BACKEND = process.env.BACKEND_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/settings/google-email`)
    return NextResponse.json(await res.json())
  } catch {
    return NextResponse.json({ email: null })
  }
}
