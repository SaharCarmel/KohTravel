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
  FileText
} from 'lucide-react'
import { InteractiveCalendarWidget } from '@/components/calendar/InteractiveCalendarWidget'
import { calendarAPI, type CalendarEvent } from '@/lib/calendar-api'

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
    description: "View all uploaded documents"
  },
  { 
    icon: Calendar, 
    label: "Upcoming Trips", 
    query: "Show me my upcoming trips and itinerary",
    description: "See your travel schedule"
  },
  { 
    icon: Plane, 
    label: "Flight Info", 
    query: "Find all my flight information and boarding passes",
    description: "Check flight details"
  },
  { 
    icon: Hotel, 
    label: "Hotels", 
    query: "Show me all my hotel reservations and check-in details",
    description: "View accommodations"
  },
  { 
    icon: MapPin, 
    label: "Travel Summary", 
    query: "Give me a complete overview of my entire travel portfolio",
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
  const [showCalendarWidget, setShowCalendarWidget] = useState(false)
  const [calendarFeedbacks, setCalendarFeedbacks] = useState<Array<{eventId: string, feedback: string, rating: 'like' | 'dislike'}>>([])
  const [widgetKey, setWidgetKey] = useState(0) // Force re-render of widget
  const [approvedEvents, setApprovedEvents] = useState<Set<string>>(new Set())
  const [rejectedEvents, setRejectedEvents] = useState<Set<string>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sessionId = useRef<string>('')
  const sendMessageRef = useRef<((message?: string) => void) | null>(null)

  useEffect(() => {
    sessionId.current = `chat-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Handle calendar widget visibility (shown when agent creates suggestions)
  const showCalendarWidgetHandler = useCallback(() => {
    setShowCalendarWidget(true)
    setWidgetKey(prev => prev + 1) // Force refresh
    // Note: DON'T reset approved/rejected events - keep them persistent
    // across widget refreshes so previously approved events don't reappear
    // Only reset calendar feedbacks for the new session
    setCalendarFeedbacks([])
  }, [])

  // Handle event approval
  const handleEventApproved = useCallback((eventId: string, approvedEvent: CalendarEvent) => {
    // Track approved event
    setApprovedEvents(prev => new Set([...prev, eventId]))
    
    // Note: No success message here - widget stays open for continued interaction
    // Success will be summarized when widget is closed
  }, [])

  // Handle event rejection
  const handleEventRejected = useCallback((eventId: string, feedback?: string) => {
    // Track rejected event
    setRejectedEvents(prev => new Set([...prev, eventId]))
    
    if (feedback) {
      // Store feedback for agent context
      setCalendarFeedbacks(prev => [...prev, { eventId, feedback, rating: 'dislike' }])
    }
    
    // Note: No feedback message here - widget stays open for continued interaction
    // Feedback will be summarized when widget is closed
  }, [])

  // Handle event feedback
  const handleEventFeedback = useCallback((eventId: string, feedback: string, rating: 'like' | 'dislike') => {
    // Store feedback for agent context
    setCalendarFeedbacks(prev => {
      const filtered = prev.filter(f => f.eventId !== eventId);
      return [...filtered, { eventId, feedback, rating }];
    });
    
    // Note: No feedback message here - widget stays open for continued interaction
    // Feedback will be summarized when widget is closed
  }, [])

  // Handle calendar widget closure  
  const handleCalendarWidgetClosed = useCallback((allFeedbacks: Array<{eventId: string, comment: string, rating: 'like' | 'dislike' | null, eventTitle?: string}>) => {
    // Close the widget
    setShowCalendarWidget(false);
    
    // Update calendar feedbacks with all feedback
    setCalendarFeedbacks(allFeedbacks);
    
    // Generate summary message based on feedback and approvals
    const feedbackCount = allFeedbacks.length;
    const likes = allFeedbacks.filter(f => f.rating === 'like').length;
    const dislikes = allFeedbacks.filter(f => f.rating === 'dislike').length;
    const comments = allFeedbacks.filter(f => f.comment && f.comment.trim()).length;
    
    let summaryContent = `📋 Thanks for reviewing the suggestions!`;
    
    if (feedbackCount > 0 || approvedEvents.size > 0 || rejectedEvents.size > 0) {
      const actionParts = [];
      
      if (approvedEvents.size > 0) {
        actionParts.push(`${approvedEvents.size} event${approvedEvents.size > 1 ? 's' : ''} added to calendar`);
      }
      
      if (rejectedEvents.size > 0) {
        actionParts.push(`${rejectedEvents.size} event${rejectedEvents.size > 1 ? 's' : ''} skipped`);
      }
      
      if (likes > 0) {
        actionParts.push(`${likes} positive rating${likes > 1 ? 's' : ''}`);
      }
      
      if (dislikes > 0) {
        actionParts.push(`${dislikes} negative rating${dislikes > 1 ? 's' : ''}`);
      }
      
      if (comments > 0) {
        actionParts.push(`${comments} detailed comment${comments > 1 ? 's' : ''}`);
      }
      
      if (actionParts.length > 0) {
        summaryContent += ` I recorded: ${actionParts.join(', ')}. I'll use this to make better recommendations for you.`;
      }
    }
    
    // Add summary message
    const summaryMessage: Message = {
      id: `widget-closed-${Date.now()}`,
      role: 'system',
      content: summaryContent,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, summaryMessage]);

    // Prepare detailed context message for auto-sending
    if (feedbackCount > 0 || approvedEvents.size > 0 || rejectedEvents.size > 0) {
      const approvedList: string[] = [];
      const rejectedList: string[] = [];
      const ratedList: string[] = [];
      
      // Organize feedback by type with enhanced context
      allFeedbacks.forEach(f => {
        const eventName = f.eventTitle || `Event ${f.eventId}`;
        const eventTypeEmoji = f.eventType ? getEventTypeEmoji(f.eventType) : '';
        const eventDetails = `${eventTypeEmoji} ${eventName}`;
        
        // Create enhanced feedback with suggestion context
        const buildFeedbackText = (baseText: string, includeContext: boolean = true) => {
          let result = baseText;
          
          if (includeContext && f.suggestionReason) {
            result += ` (AI suggested because: ${f.suggestionReason})`;
          }
          
          if (includeContext && f.suggestionConfidence) {
            result += ` [Confidence: ${f.suggestionConfidence}/10]`;
          }
          
          return result;
        };
        
        if (approvedEvents.has(f.eventId)) {
          const approvedText = f.comment 
            ? buildFeedbackText(`${eventDetails} - "${f.comment}"`)
            : buildFeedbackText(eventDetails);
          approvedList.push(approvedText);
        } else if (rejectedEvents.has(f.eventId)) {
          const rejectedText = f.comment 
            ? buildFeedbackText(`${eventDetails} - "${f.comment}"`)
            : buildFeedbackText(eventDetails);
          rejectedList.push(rejectedText);
        } else if (f.rating || f.comment) {
          const ratingText = f.rating === 'like' ? '👍' : f.rating === 'dislike' ? '👎' : '';
          const ratedText = f.comment 
            ? buildFeedbackText(`${eventDetails} ${ratingText} - "${f.comment}"`) 
            : buildFeedbackText(`${eventDetails} ${ratingText}`);
          ratedList.push(ratedText);
        }
      });
      
      // Helper function for event type emojis
      function getEventTypeEmoji(eventType: string) {
        const emojis: Record<string, string> = {
          "flight": "✈️",
          "accommodation": "🏨",
          "activity": "🎯",
          "transport": "🚗",
          "dining": "🍽️",
          "wellness": "🧘"
        };
        return emojis[eventType] || "📅";
      }
      
      // Build formatted context message
      const contextParts: string[] = [];
      
      if (approvedList.length > 0) {
        contextParts.push(`\n✅ Approved (${approvedList.length}):\n${approvedList.map(item => `  • ${item}`).join('\n')}`);
      }
      
      if (rejectedList.length > 0) {
        contextParts.push(`\n❌ Rejected (${rejectedList.length}):\n${rejectedList.map(item => `  • ${item}`).join('\n')}`);
      }
      
      if (ratedList.length > 0) {
        contextParts.push(`\n📝 Additional Feedback:\n${ratedList.map(item => `  • ${item}`).join('\n')}`);
      }
      
      if (contextParts.length > 0) {
        const contextMessage = `Based on my feedback:${contextParts.join('')}\n\nPlease use this feedback for future suggestions.`;
        
        // Auto-send the context message after a short delay using ref
        setTimeout(() => {
          if (sendMessageRef.current) {
            sendMessageRef.current(contextMessage);
          }
        }, 1500);
      }
    }
  }, [approvedEvents, rejectedEvents])

  useEffect(() => {
    const testConnection = async () => {
      try {
        // Use environment variable for agent URL or fallback to default
        const agentURL = process.env.NEXT_PUBLIC_AGENT_URL || 'http://localhost:8001';
        const response = await fetch(`${agentURL}/health/`)
        setIsConnected(response.ok)
      } catch {
        setIsConnected(false)
      }
    }
    
    testConnection()
    // Don't fetch suggested events on initial load - only after agent interactions
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
      
      // Call KohTravel API chat endpoint (which will add context and forward to agent)
      const apiURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiURL}/api/agent/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include NextAuth session cookies
        body: JSON.stringify({
          session_id: sessionId.current,
          message: text,
          context: {
            session_data: sessionData,
            user_name: session.user.name,
            user_image: session.user.image,
            calendar_feedbacks: calendarFeedbacks
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
                    id: `tool-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    role: 'system',
                    content: `🔧 Using ${data.data.name} tool...`,
                    timestamp: new Date()
                  }
                  setMessages(prev => [...prev.slice(0, -1), toolMessage, { ...prev[prev.length - 1], content: assistantContent }])
                  
                  // Check if agent is creating suggestions or showing calendar widget
                  if (data.data.name === 'show_suggested_events_carousel' || data.data.name === 'suggest_calendar_event') {
                    // Show calendar widget when agent creates suggestions
                    setTimeout(() => {
                      showCalendarWidgetHandler()
                    }, 1000)
                  }
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
      // Calendar widget is now controlled by agent via tool calls
    }
  }, [input, isLoading, session, calendarFeedbacks])

  // Assign sendMessage to ref for use in callbacks
  useEffect(() => {
    sendMessageRef.current = sendMessage
  }, [sendMessage])

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
      .map(msg => `${msg.role === 'user' ? 'You' : 'Assistant'}: ${msg.content}`)
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
      <div className="fixed inset-x-0 bottom-0 bg-slate-50 flex items-center justify-center" style={{top: 'var(--header-height, 60px)'}}>
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-slate-600" />
          <p className="text-slate-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (status === 'unauthenticated') {
    return (
      <div className="fixed inset-x-0 bottom-0 bg-slate-50 flex items-center justify-center" style={{top: 'var(--header-height, 60px)'}}>
        <div className="max-w-sm w-full space-y-6 text-center p-6">
          <div className="space-y-4">
            <Bot className="h-16 w-16 mx-auto text-slate-600" />
            <div className="space-y-2">
              <h1 className="text-2xl font-semibold text-slate-900">
                Travel Assistant
              </h1>
              <p className="text-slate-600">
                Please sign in to continue
              </p>
            </div>
          </div>
          <Button 
            onClick={() => window.location.href = '/auth/signin'} 
            className="w-full"
          >
            Sign In
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-x-0 top-0 bottom-0 bg-slate-50 flex flex-col" style={{top: 'var(--header-height, 60px)'}}>
      {/* Header - Fixed */}
      <header className="flex-shrink-0 border-b bg-white/95 backdrop-blur-sm">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-900 to-slate-700 flex items-center justify-center shadow-sm">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-slate-900">Travel Assistant</h1>
                <div className="flex items-center gap-2 mt-1">
                  <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                  <span className="text-sm text-slate-600">
                    {isConnected ? "Online" : "Offline"}
                  </span>
                </div>
              </div>
            </div>
            
            {messages.length > 0 && (
              <div className="flex items-center gap-3">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={copyConversation}
                  className="hover:bg-slate-50 border-slate-200"
                >
                  {copied ? (
                    <>
                      <CheckCheck className="h-4 w-4 text-green-600" />
                      <span className="ml-2 text-green-600">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4" />
                      <span className="ml-2">Copy</span>
                    </>
                  )}
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={clearChat}
                  className="hover:bg-red-50 border-slate-200 hover:border-red-200 hover:text-red-600"
                >
                  <Trash2 className="h-4 w-4" />
                  <span className="ml-2">Clear</span>
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Messages - Scrollable */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center p-8">
            <div className="max-w-3xl w-full text-center">
              {/* Welcome */}
              <div className="mb-12">
                <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-6">
                  <Bot className="h-8 w-8 text-slate-600" />
                </div>
                
                <h1 className="text-3xl font-bold text-slate-900 mb-4">
                  Welcome to your Travel Assistant
                </h1>
                
                <p className="text-lg text-slate-600 max-w-xl mx-auto">
                  I can help you organize your travel documents, find booking details, 
                  and plan your trips more efficiently.
                </p>
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {QUICK_ACTIONS.map((action, index) => {
                  const IconComponent = action.icon
                  return (
                    <Button
                      key={index}
                      variant="outline"
                      onClick={() => sendMessage(action.query)}
                      disabled={isLoading || !isConnected}
                      className="h-auto p-6 text-left justify-start flex flex-col items-start gap-3 hover:bg-slate-50"
                    >
                      <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                        <IconComponent className="h-5 w-5 text-slate-600" />
                      </div>
                      
                      <div className="space-y-1">
                        <h3 className="font-medium text-slate-900">
                          {action.label}
                        </h3>
                        <p className="text-sm text-slate-500">
                          {action.description}
                        </p>
                      </div>
                    </Button>
                  )
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="px-4 py-6 space-y-6 max-w-3xl mx-auto">
            {messages.map((message, index) => {
              // Check if this is the last assistant message and not streaming
              const isLastAssistantMessage = message.role === 'assistant' && 
                !message.streaming && 
                index === messages.length - 1;

              return (
                <div key={message.id}>
                  <div className={`flex items-start gap-3 ${
                    message.role === 'user' ? 'flex-row-reverse' : ''
                  }`}>
                    {/* Avatar */}
                    <div className="flex-shrink-0">
                      {message.role === 'user' ? (
                        <div className="w-8 h-8 rounded-full bg-slate-900 flex items-center justify-center">
                          <User className="h-4 w-4 text-white" />
                        </div>
                      ) : message.role === 'assistant' ? (
                        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
                          <Bot className="h-4 w-4 text-slate-600" />
                        </div>
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center">
                          <FileText className="h-4 w-4 text-slate-600" />
                        </div>
                      )}
                    </div>

                    {/* Message Content */}
                    <div className={`flex-1 ${message.role === 'user' ? 'text-right' : ''}`}>
                      <div
                        className={`inline-block rounded-2xl px-4 py-3 max-w-[85%] ${
                          message.role === 'user'
                            ? 'bg-slate-900 text-white'
                            : message.role === 'system'
                            ? 'bg-amber-50 text-amber-800 border border-amber-200 text-sm'
                            : 'bg-white border border-slate-200'
                        }`}
                      >
                        <p className="whitespace-pre-wrap leading-relaxed">
                          {message.content}
                        </p>
                        
                        {message.streaming && (
                          <div className="flex items-center gap-2 mt-3 pt-2 border-t border-slate-200">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm opacity-70">Typing...</span>
                          </div>
                        )}
                      </div>
                      
                      {/* Timestamp */}
                      <div className={`text-xs text-slate-400 mt-1 ${
                        message.role === 'user' ? 'text-right' : 'text-left'
                      }`}>
                        {message.timestamp.toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Show Interactive Calendar Widget after agent suggests events */}
                  {isLastAssistantMessage && showCalendarWidget && (
                    <div className="mt-6 mb-4">
                      <InteractiveCalendarWidget
                        key={widgetKey}
                        compact={true}
                        showOnlySuggested={true}
                        enableInteractions={true}
                        showCloseButton={true}
                        maxHeight="500px"
                        onEventApproved={handleEventApproved}
                        onEventRejected={handleEventRejected}
                        onEventFeedback={handleEventFeedback}
                        onWidgetClosed={handleCalendarWidgetClosed}
                        approvedEventIds={approvedEvents}
                        rejectedEventIds={rejectedEvents}
                        className="border-2 border-blue-200 rounded-lg bg-gradient-to-br from-blue-50 to-indigo-50"
                      />
                    </div>
                  )}
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area - Fixed */}
      <footer className="flex-shrink-0 border-t bg-white p-4">
        <div className="flex items-center gap-3 max-w-3xl mx-auto">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isConnected ? "Type your message..." : "Connecting..."}
            disabled={isLoading || !isConnected}
            className="flex-1"
          />
          <Button 
            onClick={() => sendMessage()}
            disabled={!input.trim() || isLoading || !isConnected}
            size="icon"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        
        {!isConnected && (
          <div className="text-center mt-2">
            <Badge variant="destructive" className="text-xs">
              Connection lost
            </Badge>
          </div>
        )}
      </footer>
    </div>
  )
}