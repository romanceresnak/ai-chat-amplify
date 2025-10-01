import { NextConfig } from 'next'

const nextConfig: NextConfig = {
  output: 'standalone',
  images: {
    unoptimized: true
  },
  trailingSlash: true,
  experimental: {
    outputFileTracingRoot: undefined
  }
}

export default nextConfig