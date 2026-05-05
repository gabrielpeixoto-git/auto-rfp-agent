/** @type {import('next').NextConfig} */
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://api:8000';

console.log('[NEXT CONFIG] API_URL:', API_URL);

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    const rewrites = [
      {
        source: '/api/v1/:path*',
        destination: `${API_URL}/:path*`,
      },
    ];
    console.log('[NEXT CONFIG] Rewrites configured:', JSON.stringify(rewrites));
    return rewrites;
  },
  // Security headers including CSP
  async headers() {
    const isDev = process.env.NODE_ENV === 'development';

    // CSP configuration for development vs production
    const cspDirectives = isDev
      ? [
          "default-src 'self'",
          "script-src 'self' 'unsafe-eval' 'unsafe-inline'", // Allow inline scripts in dev
          "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: blob:",
          "font-src 'self'",
          "connect-src 'self' http://localhost:* http://127.0.0.1:* /api", // Allow local API
          "frame-ancestors 'none'",
          "base-uri 'self'",
          "form-action 'self'"
        ]
      : [
          "default-src 'self'",
          "script-src 'self' 'unsafe-eval'", // Production: no unsafe-inline, use nonce or hash
          "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: blob:",
          "font-src 'self'",
          "connect-src 'self' /api",
          "frame-ancestors 'none'",
          "base-uri 'self'",
          "form-action 'self'"
        ];

    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: cspDirectives.join('; ')
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()'
          }
        ]
      }
    ];
  }
};

module.exports = nextConfig;
