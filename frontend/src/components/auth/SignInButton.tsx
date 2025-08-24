'use client'

import { signIn, signOut, useSession } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { Github, Mail } from 'lucide-react'

export default function SignInButton() {
  const { data: session, status } = useSession()

  if (status === 'loading') {
    return <Button disabled>Loading...</Button>
  }

  if (session) {
    return (
      <div className="flex items-center gap-4">
        <span className="text-sm">
          Welcome, {session.user?.name || session.user?.email}
        </span>
        <Button 
          onClick={() => signOut()} 
          variant="outline"
        >
          Sign Out
        </Button>
      </div>
    )
  }

  return (
    <div className="flex gap-2">
      <Button 
        onClick={() => signIn('github')}
        className="flex items-center gap-2"
      >
        <Github size={16} />
        GitHub
      </Button>
      <Button 
        onClick={() => signIn('google')}
        variant="outline"
        className="flex items-center gap-2"
      >
        <Mail size={16} />
        Google
      </Button>
    </div>
  )
}