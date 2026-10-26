import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Google client IDs are public identifiers. This fallback supports the
  // CLIENT_ID variable already added to the Vercel project.
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID:
      process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || process.env.CLIENT_ID || "",
  },
}

export default nextConfig
