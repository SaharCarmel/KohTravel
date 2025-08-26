/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: require('path').join(__dirname, '../'),
  async rewrites() {
    const apiPort = process.env.API_PORT || '8000';
    const apiHost = process.env.API_HOST || '127.0.0.1';
    const apiBaseUrl = `http://${apiHost}:${apiPort}`;
    
    return [
      {
        source: '/api/documents',
        destination: `${apiBaseUrl}/api/documents/`
      },
      {
        source: '/api/documents/',
        destination: `${apiBaseUrl}/api/documents/`
      },
      {
        source: '/api/documents/:id',
        destination: `${apiBaseUrl}/api/documents/:id`
      },
      {
        source: '/api/documents/:id/',
        destination: `${apiBaseUrl}/api/documents/:id`
      },
      {
        source: '/api/documents/:path*',
        destination: `${apiBaseUrl}/api/documents/:path*`
      },
      {
        source: '/api/health',
        destination: `${apiBaseUrl}/api/health`
      },
      {
        source: '/api/chat/:path*',
        destination: `${apiBaseUrl}/api/chat/:path*`
      }
    ]
  }
};

module.exports = nextConfig;