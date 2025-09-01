import { NextRequest, NextResponse } from 'next/server'
import { decode } from 'next-auth/jwt'

export async function POST(request: NextRequest) {
  try {
    const { token } = await request.json()
    
    if (!token) {
      return NextResponse.json({ success: false, error: 'Token is required' }, { status: 400 })
    }

    const decoded = await decode({
      token,
      secret: process.env.NEXTAUTH_SECRET!,
    })

    if (decoded) {
      return NextResponse.json({
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
      })
    } else {
      return NextResponse.json({ success: false, error: 'Invalid token' }, { status: 401 })
    }
  } catch (error) {
    return NextResponse.json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Token validation failed' 
    }, { status: 500 })
  }
}