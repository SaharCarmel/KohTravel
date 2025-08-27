'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Send, 
  Bot, 
  User, 
  Copy, 
  CheckCheck, 
  Loader2, 
  Trash2,
  Plane,
  Hotel,
  MapPin,
  Calendar,
  FileText,
  Sparkles
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  streaming?: boolean
}

interface StreamChunk {
  type: 'content' | 'tool_call' | 'tool_result' | 'error' | 'done'
  data: any
  timestamp: string
}

const QUICK_ACTIONS = [
  { 
    icon: FileText, 
    label: "My Documents", 
    query: "What travel documents do I have?",
    gradient: "from-blue-500 to-blue-600",
    description: "View all uploaded documents"
  },
  { 
    icon: Calendar, 
    label: "Upcoming Trips", 
    query: "Show me my upcoming trips and itinerary",
    gradient: "from-emerald-500 to-emerald-600",
    description: "See your travel schedule"
  },
  { 
    icon: Plane, 
    label: "Flight Info", 
    query: "Find all my flight information and boarding passes",
    gradient: "from-violet-500 to-violet-600",
    description: "Check flight details & gates"
  },
  { 
    icon: Hotel, 
    label: "Hotels", 
    query: "Show me all my hotel reservations and check-in details",
    gradient: "from-amber-500 to-amber-600",
    description: "View accommodation bookings"
  },
  { 
    icon: MapPin, 
    label: "Travel Summary", 
    query: "Give me a complete overview of my entire travel portfolio",
    gradient: "from-rose-500 to-rose-600",
    description: "Complete trip overview"
  }
]

export default function ChatPage() {
  const { data: session, status } = useSession()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [copied, setCopied] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sessionId = useRef<string>('')

  useEffect(() => {
    sessionId.current = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const testConnection = async () => {
      try {
        const response = await fetch('http://localhost:8001/health/')
        setIsConnected(response.ok)
      } catch {
        setIsConnected(false)
      }
    }
    
    testConnection()
    const interval = setInterval(testConnection, 30000)
    return () => clearInterval(interval)
  }, [])

  const sendMessage = useCallback(async (messageText?: string) => {
    const text = messageText || input.trim()
    if (!text || isLoading || !session?.user?.email) return

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    const assistantId = `assistant-${Date.now()}`
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      streaming: true
    }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const sessionResponse = await fetch('/api/auth/session')
      const sessionData = await sessionResponse.json()
      
      const response = await fetch('/api/agent/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionData?.accessToken || 'dev_token'}`,
        },
        body: JSON.stringify({
          session_id: sessionId.current,
          message: text,
          user_id: session.user.email,
          project: 'kohtravel',
          context: {
            session_data: sessionData,
            user_name: session.user.name,
            user_image: session.user.image
          }
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data: StreamChunk = JSON.parse(line.slice(6))
                
                if (data.type === 'content') {
                  assistantContent += data.data.content || ''
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantId 
                      ? { ...msg, content: assistantContent }
                      : msg
                  ))
                } else if (data.type === 'tool_call') {
                  const toolMessage: Message = {
                    id: `tool-${Date.now()}`,
                    role: 'system',
                    content: `🔧 Using ${data.data.name} tool...`,
                    timestamp: new Date()
                  }
                  setMessages(prev => [...prev.slice(0, -1), toolMessage, { ...prev[prev.length - 1], content: assistantContent }])
                } else if (data.type === 'error') {
                  assistantContent += `\n\n❌ Error: ${data.data.error}`
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantId 
                      ? { ...msg, content: assistantContent, streaming: false }
                      : msg
                  ))
                } else if (data.type === 'done') {
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantId 
                      ? { ...msg, content: assistantContent, streaming: false }
                      : msg
                  ))
                  break
                }
              } catch (e) {
                console.warn('Failed to parse SSE data:', line)
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error)
      setMessages(prev => prev.map(msg => 
        msg.id === assistantId 
          ? { 
              ...msg, 
              content: '❌ Sorry, I encountered an error. Please make sure the agent service is running.', 
              streaming: false 
            }
          : msg
      ))
    } finally {
      setIsLoading(false)
    }
  }, [input, isLoading, session])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const clearChat = () => {
    setMessages([])
    sessionId.current = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  const copyConversation = async () => {
    const conversationText = messages
      .filter(msg => msg.role === 'user' || msg.role === 'assistant')
      .map(msg => `${msg.role === 'user' ? '👤 You' : '🤖 Assistant'}: ${msg.content}`)
      .join('\n\n')
    
    try {
      await navigator.clipboard.writeText(conversationText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  if (status === 'loading') {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center mx-auto animate-pulse">
            <Bot className="h-8 w-8 text-white" />
          </div>
          <div className="space-y-2">
            <Loader2 className="h-6 w-6 animate-spin mx-auto text-blue-600" />
            <p className="text-muted-foreground">Connecting to your travel assistant...</p>
          </div>
        </div>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        <div className="max-w-md w-full space-y-6 text-center p-6">
          <div className="space-y-4">
            <div className="w-20 h-20 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center mx-auto">
              <Bot className="h-10 w-10 text-white" />
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                KohTravel Assistant
              </h1>
              <p className="text-muted-foreground text-lg">
                Your AI-powered travel companion awaits
              </p>
            </div>
          </div>
          <Button 
            onClick={() => window.location.href = '/auth/signin'} 
            className="w-full h-12 text-lg bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700"
          >
            Sign In to Continue
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      {/* Gradient Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 via-indigo-50/30 to-purple-50/50 pointer-events-none" />
      
      {/* Header */}
      <header className="relative border-b bg-white/80 backdrop-blur-md shadow-sm">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Travel Assistant</h1>
                <div className="flex items-center gap-2">
                  <Badge 
                    variant={isConnected ? "default" : "destructive"} 
                    className={`text-xs ${isConnected ? 'bg-green-100 text-green-800 border-green-200' : ''}`}
                  >
                    {isConnected ? "🟢 Online" : "🔴 Offline"}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button variant="ghost" size="sm" onClick={copyConversation} className="h-9">
                {copied ? (
                  <>
                    <CheckCheck className="h-4 w-4 text-green-600" />
                    <span className="ml-2 text-green-600">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    <span className="ml-2">Copy Chat</span>
                  </>
                )}
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={clearChat} className="h-9">
              <Trash2 className="h-4 w-4" />
              <span className="ml-2">Clear</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 relative overflow-hidden">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center p-8">
            <div className="max-w-4xl w-full">
              {/* Hero Section */}
              <div className="text-center mb-12">
                <div className="relative inline-block mb-6">
                  <div className="w-24 h-24 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center mx-auto shadow-2xl shadow-blue-500/25">
                    <Sparkles className="h-12 w-12 text-white" />
                  </div>
                  <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-green-500 flex items-center justify-center shadow-lg">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                </div>
                
                <h1 className="text-4xl md:text-5xl font-bold mb-4">
                  <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-transparent">
                    Welcome to KohTravel
                  </span>
                </h1>
                
                <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed">
                  Your intelligent travel companion that understands your documents, 
                  organizes your trips, and helps you travel smarter
                </p>

                <div className="flex items-center justify-center gap-2 text-sm text-gray-500 mb-10">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span>AI-Powered</span>
                  </div>
                  <span>•</span>
                  <span>Instant Responses</span>
                  <span>•</span>
                  <span>Document Analysis</span>
                </div>
              </div>

              {/* Quick Action Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {QUICK_ACTIONS.map((action, index) => {
                  const IconComponent = action.icon
                  return (
                    <button
                      key={index}
                      onClick={() => sendMessage(action.query)}
                      disabled={isLoading || !isConnected}
                      className={`group relative p-6 rounded-2xl border-2 text-left transition-all duration-300 hover:scale-105 hover:shadow-xl bg-white/60 backdrop-blur-sm ${
                        isConnected 
                          ? 'hover:border-gray-300 hover:bg-white/80 cursor-pointer' 
                          : 'opacity-50 cursor-not-allowed border-gray-200'
                      }`}
                    >
                      {/* Gradient Background */}
                      <div className={`absolute inset-0 rounded-2xl bg-gradient-to-br ${action.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-300`} />
                      
                      {/* Icon */}
                      <div className={`w-14 h-14 rounded-xl bg-gradient-to-r ${action.gradient} flex items-center justify-center mb-4 shadow-lg group-hover:shadow-xl transition-shadow duration-300`}>
                        <IconComponent className="h-7 w-7 text-white" />
                      </div>
                      
                      {/* Content */}
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold text-gray-900 group-hover:text-gray-800">
                          {action.label}
                        </h3>
                        <p className="text-sm text-gray-600 leading-relaxed">
                          {action.description}
                        </p>
                        <p className="text-xs text-gray-400 italic">
                          "{action.query}"
                        </p>
                      </div>
                      
                      {/* Hover Arrow */}
                      <div className="absolute top-4 right-4 w-8 h-8 rounded-full bg-white/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                        <Send className="h-4 w-4 text-gray-600" />
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Bottom CTA */}
              <div className="text-center mt-10">
                <p className="text-gray-500 text-sm mb-4">
                  Or type your own question below
                </p>
                <div className="flex items-center justify-center gap-1 text-xs text-gray-400">
                  <Sparkles className="h-3 w-3" />
                  <span>Powered by advanced AI technology</span>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto">
            <div className="px-4 py-6 space-y-6 max-w-4xl mx-auto min-h-full">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex items-start gap-4 ${
                    message.role === 'user' ? 'flex-row-reverse' : ''
                  }`}
                >
                  {/* Avatar */}
                  <div className="flex-shrink-0">
                    {message.role === 'user' ? (
                      <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
                        <User className="h-5 w-5 text-white" />
                      </div>
                    ) : message.role === 'assistant' ? (
                      <div className="w-10 h-10 rounded-full bg-gradient-to-r from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
                        <Bot className="h-5 w-5 text-white" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-gradient-to-r from-amber-500 to-orange-600 flex items-center justify-center shadow-lg">
                        <FileText className="h-5 w-5 text-white" />
                      </div>
                    )}
                  </div>

                  {/* Message Content */}
                  <div className={`flex-1 min-w-0 ${message.role === 'user' ? 'text-right' : ''}`}>
                    <div
                      className={`inline-block rounded-3xl px-6 py-4 max-w-[85%] shadow-lg ${
                        message.role === 'user'
                          ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
                          : message.role === 'system'
                          ? 'bg-gradient-to-r from-amber-100 to-orange-100 text-amber-900 border border-amber-200'
                          : 'bg-white border border-gray-200'
                      }`}
                    >
                      <p className="whitespace-pre-wrap leading-relaxed text-base">
                        {message.content}
                      </p>
                      
                      {message.streaming && (
                        <div className="flex items-center gap-3 mt-4 pt-3 border-t border-white/20">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '0ms' }} />
                            <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '150ms' }} />
                            <div className="w-2 h-2 rounded-full bg-white/60 animate-bounce" style={{ animationDelay: '300ms' }} />
                          </div>
                          <span className="text-sm opacity-80">Assistant is thinking...</span>
                        </div>
                      )}
                    </div>
                    
                    {/* Timestamp */}
                    <div className={`text-xs text-gray-400 mt-2 ${
                      message.role === 'user' ? 'text-right' : 'text-left'
                    }`}>
                      {message.timestamp.toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                      })}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <footer className="relative border-t bg-white/80 backdrop-blur-md">
        <div className="p-6">
          <div className="flex items-end gap-4 max-w-4xl mx-auto">
            <div className="flex-1">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  isConnected 
                    ? "Ask me anything about your travels... ✈️" 
                    : "Connecting to your travel assistant..."
                }
                disabled={isLoading || !isConnected}
                className="h-14 text-base rounded-full border-2 border-gray-200 focus:border-blue-500 px-6 shadow-lg bg-white/90 backdrop-blur-sm placeholder:text-gray-400"
              />
            </div>
            <Button 
              onClick={() => sendMessage()}
              disabled={!input.trim() || isLoading || !isConnected}
              className={`h-14 w-14 rounded-full flex-shrink-0 shadow-lg transition-all duration-300 ${
                input.trim() && isConnected && !isLoading
                  ? 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 hover:scale-110'
                  : 'bg-gray-300'
              }`}
            >
              {isLoading ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                <Send className="h-6 w-6" />
              )}
            </Button>
          </div>
          
          {!isConnected && (
            <div className="text-center mt-4">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-100 text-red-800 border border-red-200">
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-sm font-medium">Connection Lost - Reconnecting...</span>
              </div>
            </div>
          )}
        </div>
      </footer>
    </div>
  )
}