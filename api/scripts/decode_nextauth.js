#!/usr/bin/env node

/**
 * NextAuth.js token decoder for FastAPI backend
 * Uses official next-auth/jwt library for proper token validation
 */

const { decode } = require('next-auth/jwt');

async function decodeToken() {
  try {
    const args = process.argv.slice(2);
    if (args.length !== 2) {
      console.error(JSON.stringify({ error: 'Usage: node decode_nextauth.js <token> <secret>' }));
      process.exit(1);
    }

    const [token, secret] = args;

    const decoded = await decode({
      token: token,
      secret: secret,
    });

    if (decoded) {
      console.log(JSON.stringify({
        success: true,
        user: {
          user_id: decoded.sub,
          email: decoded.email,
          name: decoded.name,
          image: decoded.picture || decoded.image,
          provider: decoded.provider || 'unknown',
          exp: decoded.exp,
          iat: decoded.iat
        }
      }));
    } else {
      console.log(JSON.stringify({ success: false, error: 'Token validation failed' }));
    }
  } catch (error) {
    console.log(JSON.stringify({ success: false, error: error.message }));
  }
}

decodeToken();