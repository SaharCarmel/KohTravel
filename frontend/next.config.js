/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/documents',
        destination: 'http://127.0.0.1:8000/api/documents/'
      },
      {
        source: '/api/documents/',
        destination: 'http://127.0.0.1:8000/api/documents/'
      },
      {
        source: '/api/documents/:id',
        destination: 'http://127.0.0.1:8000/api/documents/:id'
      },
      {
        source: '/api/documents/:id/',
        destination: 'http://127.0.0.1:8000/api/documents/:id'
      },
      {
        source: '/api/documents/:path*',
        destination: 'http://127.0.0.1:8000/api/documents/:path*'
      },
      {
        source: '/api/health',
        destination: 'http://127.0.0.1:8000/api/health'
      }
    ]
  }
};

module.exports = nextConfig;