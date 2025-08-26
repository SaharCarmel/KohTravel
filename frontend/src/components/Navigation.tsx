'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import SignInButton from '@/components/auth/SignInButton'
import { Home, FileText, MessageSquare, Plane, DollarSign } from 'lucide-react'

export default function Navigation() {
  const pathname = usePathname()
  
  const navItems = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/chat', label: 'Chat', icon: MessageSquare },
    { href: '/documents', label: 'Documents', icon: FileText },
    { href: '/planning', label: 'Planning', icon: Plane, disabled: true },
    { href: '/expenses', label: 'Expenses', icon: DollarSign, disabled: true },
  ]

  return (
    <header className="border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link href="/" className="text-xl font-bold text-primary">
              KohTravel
            </Link>
            
            <nav className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                
                return (
                  <Link key={item.href} href={item.href}>
                    <Button
                      variant={isActive ? "default" : "ghost"}
                      size="sm"
                      disabled={item.disabled}
                      className="flex items-center gap-2"
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Button>
                  </Link>
                )
              })}
            </nav>
          </div>

          <div className="flex items-center space-x-2">
            <SignInButton />
          </div>
        </div>

        {/* Mobile Navigation */}
        <nav className="md:hidden mt-3 flex items-center space-x-1 overflow-x-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = pathname === item.href
            
            return (
              <Link key={item.href} href={item.href}>
                <Button
                  variant={isActive ? "default" : "ghost"}
                  size="sm"
                  disabled={item.disabled}
                  className="flex items-center gap-1 whitespace-nowrap"
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Button>
              </Link>
            )
          })}
        </nav>
      </div>
    </header>
  )
}