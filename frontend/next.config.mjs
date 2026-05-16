/** @type {import('next').NextConfig} */
const nextConfig = {
  // BACKEND_URL is set at build/runtime in Vercel dashboard
  // Falls back to localhost for local development
  env: {
    BACKEND_URL: process.env.BACKEND_URL || 'http://localhost:8000',
  },
}

export default nextConfig
