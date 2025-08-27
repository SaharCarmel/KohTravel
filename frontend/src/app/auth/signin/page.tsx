'use client'

import { getProviders, signIn } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Github, Mail } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

function SignInContent() {
  const searchParams = useSearchParams()
  const error = searchParams.get('error')

  return (
    <div className="full-height flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Sign in to KohTravel</CardTitle>
          {error && (
            <p className="text-sm text-red-600 mt-2">
              Authentication error. Please try again.
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <Button 
            onClick={() => signIn('github', { callbackUrl: '/' })}
            className="w-full flex items-center gap-2"
          >
            <Github size={16} />
            Continue with GitHub
          </Button>
          <Button 
            onClick={() => signIn('google', { callbackUrl: '/' })}
            variant="outline"
            className="w-full flex items-center gap-2"
          >
            <Mail size={16} />
            Continue with Google
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default function SignInPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SignInContent />
    </Suspense>
  )
}