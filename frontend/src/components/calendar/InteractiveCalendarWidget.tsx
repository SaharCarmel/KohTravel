"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, isSameDay, isToday, addMonths, subMonths, startOfDay, endOfDay, addWeeks, subWeeks, addDays as addDaysUtility } from "date-fns";
import { ChevronLeft, ChevronRight, Check, X, ThumbsUp, ThumbsDown, MessageCircle, Calendar, Clock, MapPin, Star, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { calendarAPI, type CalendarEvent } from "@/lib/calendar-api";

interface InteractiveCalendarWidgetProps {
  // Calendar view props
  className?: string;
  initialDate?: Date;
  compact?: boolean; // For chat integration
  
  // Event interaction props
  onEventApproved?: (eventId: string, approvedEvent: CalendarEvent) => void;
  onEventRejected?: (eventId: string, feedback?: string) => void;
  onEventFeedback?: (eventId: string, feedback: string, rating: 'like' | 'dislike') => void;
  onWidgetClosed?: (allFeedbacks: EventFeedback[]) => void;
  
  // Chat integration
  showOnlySuggested?: boolean;
  enableInteractions?: boolean;
  maxHeight?: string;
  showCloseButton?: boolean;
  approvedEventIds?: Set<string>;
  rejectedEventIds?: Set<string>;
}

interface EventFeedback {
  eventId: string;
  comment: string;
  rating: 'like' | 'dislike' | null;
  eventTitle?: string;
  eventType?: string;
  suggestionReason?: string;
  suggestionConfidence?: number;
  action?: 'approved' | 'rejected' | 'feedback';
}

// Convert API event to display format
const convertEvent = (apiEvent: CalendarEvent) => {
  const startDate = new Date(apiEvent.start_datetime);
  return {
    id: apiEvent.id,
    title: apiEvent.title,
    date: startDate,
    time: format(startDate, "HH:mm"),
    type: apiEvent.event_type,
    color: apiEvent.color || getDefaultColor(apiEvent.event_type),
    description: apiEvent.description || apiEvent.location || '',
    location: apiEvent.location,
    status: apiEvent.status,
    isSuggested: apiEvent.status === 'suggested',
    suggestionReason: apiEvent.suggestion_reason,
    suggestionConfidence: apiEvent.suggestion_confidence,
    startDateTime: apiEvent.start_datetime,
    endDateTime: apiEvent.end_datetime,
    allDay: apiEvent.all_day,
  };
};

const getDefaultColor = (eventType: string) => {
  const colors: Record<string, string> = {
    "flight": "bg-blue-500",
    "accommodation": "bg-green-500",
    "activity": "bg-purple-500",
    "transport": "bg-cyan-500",
    "dining": "bg-yellow-500",
    "wellness": "bg-pink-500"
  };
  return colors[eventType] || "bg-gray-500";
};

const getEventTypeIcon = (eventType: string) => {
  const icons: Record<string, string> = {
    "flight": "✈️",
    "accommodation": "🏨",
    "activity": "🎯",
    "transport": "🚗",
    "dining": "🍽️",
    "wellness": "🧘"
  };
  return icons[eventType] || "📅";
};

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 8) return "text-green-600 bg-green-50";
  if (confidence >= 6) return "text-yellow-600 bg-yellow-50";
  return "text-red-600 bg-red-50";
};

type Event = ReturnType<typeof convertEvent>;

export function InteractiveCalendarWidget({
  className = "",
  initialDate = new Date(),
  compact = false,
  onEventApproved,
  onEventRejected,
  onEventFeedback,
  onWidgetClosed,
  showOnlySuggested = false,
  enableInteractions = false,
  maxHeight = "400px",
  showCloseButton = false,
  approvedEventIds = new Set(),
  rejectedEventIds = new Set()
}: InteractiveCalendarWidgetProps) {
  const [currentDate, setCurrentDate] = useState(initialDate);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const [eventFeedbacks, setEventFeedbacks] = useState<Map<string, EventFeedback>>(new Map());
  const [approvedEvents, setApprovedEvents] = useState<Set<string>>(new Set());
  const [rejectedEvents, setRejectedEvents] = useState<Set<string>>(new Set());
  const [isActionInProgress, setIsActionInProgress] = useState(false);
  const [currentEventIndex, setCurrentEventIndex] = useState(0);
  const [viewMode, setViewMode] = useState<'month' | 'week' | 'day'>('month');
  const [showDatePicker, setShowDatePicker] = useState(false);
  const datePickerRef = useRef<HTMLDivElement>(null);

  // Close date picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (datePickerRef.current && !datePickerRef.current.contains(event.target as Node)) {
        setShowDatePicker(false);
      }
    };

    if (showDatePicker) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showDatePicker]);

  // Get suggested events for navigation (exclude already approved/rejected)
  const pendingSuggestedEvents = events.filter(event => 
    event.isSuggested && 
    !approvedEventIds.has(event.id) && 
    !rejectedEventIds.has(event.id)
  );
  const hasSuggestedEvents = pendingSuggestedEvents.length > 0;
  const isMultipleSuggestions = pendingSuggestedEvents.length > 1;

  // Navigate to previous suggested event
  const goToPreviousEvent = () => {
    if (!hasSuggestedEvents) return;
    const newIndex = currentEventIndex > 0 ? currentEventIndex - 1 : pendingSuggestedEvents.length - 1;
    setCurrentEventIndex(newIndex);
    setSelectedEvent(pendingSuggestedEvents[newIndex]);
  };

  // Navigate to next suggested event
  const goToNextEvent = () => {
    if (!hasSuggestedEvents) return;
    const newIndex = currentEventIndex < pendingSuggestedEvents.length - 1 ? currentEventIndex + 1 : 0;
    setCurrentEventIndex(newIndex);
    setSelectedEvent(pendingSuggestedEvents[newIndex]);
  };

  // Auto-select first pending suggested event when events change
  useEffect(() => {
    if (hasSuggestedEvents && !selectedEvent) {
      setCurrentEventIndex(0);
      setSelectedEvent(pendingSuggestedEvents[0]);
    } else if (selectedEvent && !pendingSuggestedEvents.find(e => e.id === selectedEvent.id)) {
      // If current selected event is no longer in pending suggestions, select first available
      if (hasSuggestedEvents) {
        setCurrentEventIndex(0);
        setSelectedEvent(pendingSuggestedEvents[0]);
      } else {
        // Keep the selected event visible even if approved/rejected
        // Don't auto-clear it
      }
    }
  }, [events, hasSuggestedEvents, selectedEvent, pendingSuggestedEvents]);

  // Fetch events from API
  const fetchEvents = useCallback(async () => {
    try {
      setIsLoading(true);
      
      // Calculate date range based on view mode
      let startDate: Date, endDate: Date;
      
      if (viewMode === 'day') {
        // For day view: get the single day plus some buffer
        startDate = startOfDay(currentDate);
        endDate = endOfDay(currentDate);
      } else if (viewMode === 'week') {
        // For week view: get the week containing the current date
        startDate = startOfWeek(currentDate);
        endDate = endOfWeek(currentDate);
      } else {
        // For month view: get the full month grid (including partial weeks)
        const monthStart = startOfMonth(currentDate);
        const monthEnd = endOfMonth(currentDate);
        startDate = startOfWeek(monthStart);
        endDate = endOfWeek(monthEnd);
      }
      
      const apiEvents = await calendarAPI.getEvents({
        start_date: format(startDate, 'yyyy-MM-dd'),
        end_date: format(endDate, 'yyyy-MM-dd'),
      });
      
      let convertedEvents = apiEvents.map(convertEvent);
      
      // Filter events based on context
      if (showOnlySuggested) {
        // In chat mode: show both confirmed and suggested events for full schedule visibility
        // Only exclude cancelled and tentative events
        convertedEvents = convertedEvents.filter(event => 
          event.status === 'confirmed' || event.status === 'suggested'
        );
      }
      
      // DON'T filter out approved/rejected events - keep them visible with status
      // They will be filtered from navigation logic but stay visible in calendar
      
      setEvents(convertedEvents);
    } catch (err) {
      console.error('Error fetching events:', err);
    } finally {
      setIsLoading(false);
    }
  }, [currentDate, viewMode, showOnlySuggested]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  // Listen for calendar refresh events
  useEffect(() => {
    const handleCalendarRefresh = () => {
      fetchEvents();
    };
    
    window.addEventListener('calendar-refresh', handleCalendarRefresh);
    return () => window.removeEventListener('calendar-refresh', handleCalendarRefresh);
  }, [fetchEvents]);

  // Get events for a specific date
  const getEventsForDate = (date: Date): Event[] => {
    return events.filter(event => isSameDay(event.date, date));
  };

  // Handle event approval
  const handleApproveEvent = async (event: Event) => {
    if (!enableInteractions) return;
    
    setIsActionInProgress(true);
    try {
      const approvedEvent = await calendarAPI.approveEvent(event.id, {
        approved: true,
        user_feedback: "Approved from interactive calendar"
      });
      
      setApprovedEvents(prev => new Set([...prev, event.id]));
      onEventApproved?.(event.id, approvedEvent);
      
      // Update event status in local state (optimistic update)
      setEvents(prev => prev.map(e => 
        e.id === event.id 
          ? { ...e, status: 'confirmed' as const } 
          : e
      ));
    } catch (error) {
      console.error('Failed to approve event:', error);
    } finally {
      setIsActionInProgress(false);
    }
  };

  // Handle event rejection
  const handleRejectEvent = async (event: Event, feedback?: string) => {
    if (!enableInteractions) return;
    
    setIsActionInProgress(true);
    try {
      await calendarAPI.approveEvent(event.id, {
        approved: false,
        user_feedback: feedback || "Rejected from interactive calendar"
      });
      
      setRejectedEvents(prev => new Set([...prev, event.id]));
      onEventRejected?.(event.id, feedback);
      
      // Keep event visible but mark as rejected (optimistic update)
      setEvents(prev => prev.map(e => 
        e.id === event.id 
          ? { ...e, status: 'cancelled' as const } 
          : e
      ));
    } catch (error) {
      console.error('Failed to reject event:', error);
    } finally {
      setIsActionInProgress(false);
    }
  };

  // Handle event feedback
  const handleEventFeedback = (event: Event, comment: string, rating: 'like' | 'dislike') => {
    const feedback: EventFeedback = {
      eventId: event.id,
      comment,
      rating
    };
    
    setEventFeedbacks(prev => new Map(prev.set(event.id, feedback)));
    onEventFeedback?.(event.id, comment, rating);
  };

  // Handle widget close
  const handleCloseWidget = () => {
    // Convert Map to array and pass all feedback with comprehensive event details
    const allFeedbacks = Array.from(eventFeedbacks.values()).map(feedback => {
      const event = events.find(e => e.id === feedback.eventId);
      return {
        ...feedback,
        eventTitle: event?.title || feedback.eventTitle,
        eventType: event?.type,
        suggestionReason: event?.suggestionReason,
        suggestionConfidence: event?.suggestionConfidence,
      };
    });
    onWidgetClosed?.(allFeedbacks);
  };

  // Render calendar grid based on view mode
  const renderCalendarGrid = () => {
    if (viewMode === 'day') {
      return renderDayView();
    } else if (viewMode === 'week') {
      return renderWeekView();
    } else {
      return renderMonthView();
    }
  };

  // Render month view (original implementation)
  const renderMonthView = () => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);
    
    const rows = [];
    let days = [];
    let day = startDate;

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const currentDay = day; // Capture the current day value for closures
        const dayEvents = getEventsForDate(currentDay);
        const isCurrentMonth = isSameMonth(currentDay, monthStart);
        const isSelected = selectedDate && isSameDay(currentDay, selectedDate);
        const isTodayDate = isToday(currentDay);
        
        days.push(
          <div
            key={day.toString()}
            className={cn(
              compact ? "min-h-16 p-1" : "min-h-24 p-2",
              "border border-gray-200 cursor-pointer transition-colors select-none",
              !isCurrentMonth && "bg-gray-50 text-gray-400",
              isSelected && "bg-blue-50 border-blue-300",
              isTodayDate && "bg-yellow-50 border-yellow-300",
              "hover:bg-gray-50 hover:shadow-sm"
            )}
            onClick={() => {
              setSelectedDate(currentDay);
              if (dayEvents.length > 0) {
                setSelectedEvent(dayEvents[0]);
              }
            }}
            onDoubleClick={() => {
              setCurrentDate(currentDay);
              setViewMode('day');
              setSelectedDate(currentDay);
              if (dayEvents.length > 0) {
                setSelectedEvent(dayEvents[0]);
              }
            }}
            title={`${format(currentDay, 'EEEE, MMMM d, yyyy')}${dayEvents.length > 0 ? ` (${dayEvents.length} event${dayEvents.length > 1 ? 's' : ''})` : ''} - Double-click to focus on this day`}
          >
            <div className="flex justify-between items-start mb-1">
              <span className={cn(
                compact ? "text-xs" : "text-sm",
                "font-medium",
                isTodayDate && "text-yellow-600 font-bold",
                !isCurrentMonth && "text-gray-400"
              )}>
                {format(currentDay, "d")}
              </span>
              {dayEvents.length > 0 && (
                <Badge variant="secondary" className="text-xs px-1 py-0">
                  {dayEvents.length}
                </Badge>
              )}
            </div>
            <div className="space-y-1">
              {dayEvents.slice(0, compact ? 1 : 2).map((event) => (
                <div
                  key={event.id}
                  className={cn(
                    "text-xs p-1 rounded text-white truncate relative",
                    event.color,
                    // Suggested event styling
                    event.isSuggested && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) && "opacity-70 border border-dashed border-white/50",
                    // Approved event styling
                    approvedEventIds.has(event.id) && "opacity-90 border-2 border-solid border-green-400",
                    // Rejected event styling  
                    rejectedEventIds.has(event.id) && "opacity-50 border-2 border-solid border-red-400 line-through",
                    // Confirmed event styling (default, solid appearance)
                    event.status === 'confirmed' && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) && "opacity-100 border border-solid border-white/20"
                  )}
                  title={`${event.time} - ${event.title}${event.isSuggested && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) ? ' (Suggested)' : ''}${approvedEventIds.has(event.id) ? ' (Approved ✓)' : ''}${rejectedEventIds.has(event.id) ? ' (Rejected ✗)' : ''}${event.status === 'confirmed' && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) ? ' (Confirmed)' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedEvent(event);
                  }}
                >
                  {event.isSuggested && (
                    <div className="absolute -top-1 -right-1 w-2 h-2 bg-amber-400 rounded-full border border-white" />
                  )}
                  {compact ? event.title : `${event.time} ${event.title}`}
                </div>
              ))}
              {dayEvents.length > (compact ? 1 : 2) && (
                <div className="text-xs text-gray-500 font-medium">
                  +{dayEvents.length - (compact ? 1 : 2)} more
                </div>
              )}
            </div>
          </div>
        );
        day = addDays(day, 1);
      }
      rows.push(
        <div key={day.toString()} className="grid grid-cols-7">
          {days}
        </div>
      );
      days = [];
    }

    return rows;
  };

  // Render week view
  const renderWeekView = () => {
    const weekStart = startOfWeek(currentDate);
    const weekDays = [];
    
    for (let i = 0; i < 7; i++) {
      const day = addDays(weekStart, i);
      const dayEvents = getEventsForDate(day);
      const isSelected = selectedDate && isSameDay(day, selectedDate);
      const isTodayDate = isToday(day);
      
      weekDays.push(
        <div
          key={day.toString()}
          className={cn(
            "border border-gray-200 cursor-pointer transition-colors p-3 min-h-32 select-none",
            isSelected && "bg-blue-50 border-blue-300",
            isTodayDate && "bg-yellow-50 border-yellow-300",
            "hover:bg-gray-50 hover:shadow-sm"
          )}
          onClick={() => {
            setSelectedDate(day);
            if (dayEvents.length > 0) {
              setSelectedEvent(dayEvents[0]);
            }
          }}
          onDoubleClick={() => {
            setCurrentDate(day);
            setViewMode('day');
            setSelectedDate(day);
            if (dayEvents.length > 0) {
              setSelectedEvent(dayEvents[0]);
            }
          }}
          title={`${format(day, 'EEEE, MMMM d, yyyy')}${dayEvents.length > 0 ? ` (${dayEvents.length} event${dayEvents.length > 1 ? 's' : ''})` : ''} - Double-click to focus on this day`}
        >
          <div className="flex justify-between items-center mb-2">
            <div className="text-center">
              <div className="text-xs text-gray-500 font-medium uppercase">
                {format(day, "EEE")}
              </div>
              <div className={cn(
                "text-lg font-semibold mt-1",
                isTodayDate && "text-yellow-600"
              )}>
                {format(day, "d")}
              </div>
            </div>
            {dayEvents.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {dayEvents.length}
              </Badge>
            )}
          </div>
          <div className="space-y-1">
            {dayEvents.map((event) => (
              <div
                key={event.id}
                className={cn(
                  "text-xs p-2 rounded text-white relative cursor-pointer",
                  event.color,
                  // Suggested event styling
                  event.isSuggested && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) && "opacity-70 border border-dashed border-white/50",
                  // Approved event styling
                  approvedEventIds.has(event.id) && "opacity-90 border-2 border-solid border-green-400",
                  // Rejected event styling
                  rejectedEventIds.has(event.id) && "opacity-50 border-2 border-solid border-red-400",
                  // Confirmed event styling
                  event.status === 'confirmed' && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) && "opacity-100 border border-solid border-white/20"
                )}
                title={`${event.time} - ${event.title}${event.isSuggested && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) ? ' (Suggested)' : ''}${approvedEventIds.has(event.id) ? ' (Approved ✓)' : ''}${rejectedEventIds.has(event.id) ? ' (Rejected ✗)' : ''}${event.status === 'confirmed' && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) ? ' (Confirmed)' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedEvent(event);
                }}
              >
                {event.isSuggested && (
                  <div className="absolute -top-1 -right-1 w-2 h-2 bg-amber-400 rounded-full border border-white" />
                )}
                <div className="font-medium">{event.time}</div>
                <div className="truncate">{event.title}</div>
              </div>
            ))}
          </div>
        </div>
      );
    }
    
    return [
      <div key="week" className="grid grid-cols-7">
        {weekDays}
      </div>
    ];
  };

  // Render day view
  const renderDayView = () => {
    const dayStart = startOfDay(currentDate);
    const dayEvents = getEventsForDate(dayStart);
    const isTodayDate = isToday(dayStart);
    
    return [
      <div key="day" className="border border-gray-200 rounded-lg p-4">
        <div className="text-center mb-4">
          <div className="text-sm text-gray-500 font-medium uppercase">
            {format(dayStart, "EEEE")}
          </div>
          <div className={cn(
            "text-2xl font-bold mt-1",
            isTodayDate && "text-yellow-600"
          )}>
            {format(dayStart, "d")}
          </div>
          <div className="text-sm text-gray-500">
            {format(dayStart, "MMMM yyyy")}
          </div>
        </div>
        
        <div className="space-y-2">
          {dayEvents.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              No events scheduled
            </div>
          ) : (
            dayEvents.map((event) => (
              <div
                key={event.id}
                className={cn(
                  "p-3 rounded-lg text-white relative cursor-pointer",
                  event.color,
                  // Suggested event styling
                  event.isSuggested && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) && "opacity-70 border-2 border-dashed border-white/50",
                  // Approved event styling
                  approvedEventIds.has(event.id) && "opacity-90 border-2 border-solid border-green-400",
                  // Rejected event styling
                  rejectedEventIds.has(event.id) && "opacity-50 border-2 border-solid border-red-400",
                  // Confirmed event styling
                  event.status === 'confirmed' && !approvedEventIds.has(event.id) && !rejectedEventIds.has(event.id) && "opacity-100 border-2 border-solid border-white/20"
                )}
                onClick={() => setSelectedEvent(event)}
              >
                {event.isSuggested && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-amber-400 rounded-full border border-white" />
                )}
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="font-semibold text-sm">{event.title}</div>
                    {event.description && (
                      <div className="text-xs mt-1 opacity-90">{event.description}</div>
                    )}
                  </div>
                  <div className="text-xs font-medium">
                    {event.time}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    ];
  };

  // Render event detail panel
  const renderEventDetail = () => {
    if (!selectedEvent) return null;

    const feedback = eventFeedbacks.get(selectedEvent.id);
    const isApproved = approvedEvents.has(selectedEvent.id);
    const isRejected = rejectedEvents.has(selectedEvent.id);

    return (
      <Card className="mt-4">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{getEventTypeIcon(selectedEvent.type)}</span>
              <div>
                <CardTitle className="text-lg">{selectedEvent.title}</CardTitle>
                {(selectedEvent.isSuggested || selectedEvent.status === 'confirmed') && (
                  <div className="flex items-center gap-2 mt-1">
                    {approvedEventIds.has(selectedEvent.id) ? (
                      <Badge variant="secondary" className="text-xs bg-green-200 text-green-800">
                        ✅ Approved
                      </Badge>
                    ) : rejectedEventIds.has(selectedEvent.id) ? (
                      <Badge variant="secondary" className="text-xs bg-red-200 text-red-800">
                        ❌ Rejected
                      </Badge>
                    ) : selectedEvent.status === 'confirmed' ? (
                      <Badge variant="secondary" className="text-xs bg-blue-200 text-blue-800">
                        ✓ Confirmed
                      </Badge>
                    ) : (
                      <Badge variant="secondary" className="text-xs bg-amber-200 text-amber-800">
                        ✨ Suggested
                      </Badge>
                    )}
                    {selectedEvent.suggestionConfidence && (
                      <Badge 
                        variant="secondary" 
                        className={cn("text-xs", getConfidenceColor(selectedEvent.suggestionConfidence))}
                      >
                        <Star className="h-3 w-3 mr-1" />
                        {selectedEvent.suggestionConfidence}/10
                      </Badge>
                    )}
                  </div>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedEvent(null)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Event Navigation Controls */}
          {enableInteractions && selectedEvent.isSuggested && isMultipleSuggestions && (
            <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-200">
              <Button
                variant="outline"
                size="sm"
                onClick={goToPreviousEvent}
                className="flex items-center gap-1"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600">
                  {currentEventIndex + 1} of {pendingSuggestedEvents.length} suggestions
                </span>
                {/* Progress dots */}
                <div className="flex gap-1">
                  {pendingSuggestedEvents.map((_, index) => (
                    <div
                      key={index}
                      className={cn(
                        "w-2 h-2 rounded-full transition-colors",
                        index === currentEventIndex ? "bg-blue-500" : "bg-slate-300"
                      )}
                    />
                  ))}
                </div>
              </div>
              
              <Button
                variant="outline"
                size="sm"
                onClick={goToNextEvent}
                className="flex items-center gap-1"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardHeader>
        
        <CardContent className="space-y-4">
          {/* Event Details */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Calendar className="h-4 w-4" />
              {format(new Date(selectedEvent.startDateTime), "MMM dd, yyyy")}
            </div>
            
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Clock className="h-4 w-4" />
              {selectedEvent.allDay ? (
                "All day"
              ) : (
                <>
                  {format(new Date(selectedEvent.startDateTime), "h:mm a")}
                  {selectedEvent.endDateTime && 
                    ` - ${format(new Date(selectedEvent.endDateTime), "h:mm a")}`
                  }
                </>
              )}
            </div>

            {selectedEvent.location && (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <MapPin className="h-4 w-4" />
                {selectedEvent.location}
              </div>
            )}
            
            {selectedEvent.description && (
              <p className="text-sm text-slate-600 mt-2">{selectedEvent.description}</p>
            )}
          </div>

          {/* AI Suggestion Reason */}
          {selectedEvent.suggestionReason && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Lightbulb className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-medium text-amber-800 mb-1">
                    Why I suggested this:
                  </p>
                  <p className="text-sm text-amber-700">
                    {selectedEvent.suggestionReason}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Interactive Actions for Suggested Events */}
          {enableInteractions && selectedEvent.isSuggested && !isApproved && !isRejected && (
            <div className="space-y-3 pt-2 border-t">
              <div className="flex items-center gap-2">
                <Button
                  onClick={() => handleApproveEvent(selectedEvent)}
                  disabled={isActionInProgress}
                  className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                >
                  {isActionInProgress ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Adding...
                    </div>
                  ) : (
                    <>
                      <Check className="h-4 w-4 mr-2" />
                      Add to Calendar
                    </>
                  )}
                </Button>
                
                <Button
                  onClick={() => handleRejectEvent(selectedEvent)}
                  disabled={isActionInProgress}
                  variant="outline"
                  className="border-red-200 text-red-700 hover:bg-red-50"
                >
                  <X className="h-4 w-4 mr-1" />
                  Skip
                </Button>
              </div>
              
              {/* Feedback Section */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">Rate this suggestion:</span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const newFeedback: EventFeedback = {
                        eventId: selectedEvent.id,
                        comment: feedback?.comment || '',
                        rating: 'like',
                        eventTitle: selectedEvent.title,
                        eventType: selectedEvent.type,
                        suggestionReason: selectedEvent.suggestionReason,
                        suggestionConfidence: selectedEvent.suggestionConfidence,
                        action: 'feedback'
                      };
                      setEventFeedbacks(prev => new Map(prev.set(selectedEvent.id, newFeedback)));
                      handleEventFeedback(selectedEvent, feedback?.comment || '', 'like');
                    }}
                    className={cn(
                      "text-green-600 hover:bg-green-50",
                      feedback?.rating === 'like' && "bg-green-50"
                    )}
                  >
                    <ThumbsUp className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const newFeedback: EventFeedback = {
                        eventId: selectedEvent.id,
                        comment: feedback?.comment || '',
                        rating: 'dislike',
                        eventTitle: selectedEvent.title,
                        eventType: selectedEvent.type,
                        suggestionReason: selectedEvent.suggestionReason,
                        suggestionConfidence: selectedEvent.suggestionConfidence,
                        action: 'feedback'
                      };
                      setEventFeedbacks(prev => new Map(prev.set(selectedEvent.id, newFeedback)));
                      handleEventFeedback(selectedEvent, feedback?.comment || '', 'dislike');
                    }}
                    className={cn(
                      "text-red-600 hover:bg-red-50",
                      feedback?.rating === 'dislike' && "bg-red-50"
                    )}
                  >
                    <ThumbsDown className="h-4 w-4" />
                  </Button>
                </div>
                
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-2 block">
                    Add your thoughts (optional):
                  </label>
                  <Textarea
                    placeholder="e.g., I prefer morning flights, this looks great for our family..."
                    value={feedback?.comment || ''}
                    onChange={(e) => {
                      const newFeedback: EventFeedback = {
                        eventId: selectedEvent.id,
                        comment: e.target.value,
                        rating: feedback?.rating || null,
                        eventTitle: selectedEvent.title,
                        eventType: selectedEvent.type,
                        suggestionReason: selectedEvent.suggestionReason,
                        suggestionConfidence: selectedEvent.suggestionConfidence,
                        action: 'feedback'
                      };
                      setEventFeedbacks(prev => new Map(prev.set(selectedEvent.id, newFeedback)));
                    }}
                    className="text-sm"
                    rows={2}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Status Messages */}
          {isApproved && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-green-800">
                <Check className="h-4 w-4" />
                <span className="text-sm font-medium">Added to your calendar!</span>
              </div>
            </div>
          )}
          
          {isRejected && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <div className="flex items-center gap-2 text-gray-600">
                <X className="h-4 w-4" />
                <span className="text-sm font-medium">Event skipped</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className={cn("space-y-4", className)} style={{ maxHeight }}>
      {/* Calendar Header */}
      <Card className="p-4">
        {isLoading && (
          <div className="flex items-center justify-center py-2 mb-2">
            <div className="w-4 h-4 border-2 border-slate-600 border-t-transparent rounded-full animate-spin mr-2" />
            <span className="text-sm text-slate-600">Loading events...</span>
          </div>
        )}
        
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (viewMode === 'day') {
                  setCurrentDate(prev => addDaysUtility(prev, -1));
                } else if (viewMode === 'week') {
                  setCurrentDate(prev => subWeeks(prev, 1));
                } else {
                  setCurrentDate(prev => subMonths(prev, 1));
                }
              }}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            {/* Date Display with Click-to-Edit */}
            <div className="relative">
              <h2 
                className={cn(
                  "font-semibold text-center cursor-pointer hover:text-blue-600 transition-colors",
                  compact ? "text-base min-w-32" : "text-xl min-w-48"
                )}
                onClick={() => setShowDatePicker(!showDatePicker)}
                title="Click to jump to a specific date"
              >
                {viewMode === 'day' 
                  ? format(currentDate, "MMMM d, yyyy")
                  : viewMode === 'week'
                  ? `${format(startOfWeek(currentDate), "MMM d")} - ${format(endOfWeek(currentDate), "MMM d, yyyy")}`
                  : format(currentDate, "MMMM yyyy")
                }
              </h2>
              
              {/* Date Picker Dropdown */}
              {showDatePicker && (
                <div 
                  ref={datePickerRef}
                  className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 p-3 bg-white border border-gray-200 rounded-lg shadow-lg z-50"
                >
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-700 block">
                      Jump to date:
                    </label>
                    <input
                      type="date"
                      value={format(currentDate, 'yyyy-MM-dd')}
                      onChange={(e) => {
                        if (e.target.value) {
                          setCurrentDate(new Date(e.target.value));
                          setShowDatePicker(false);
                        }
                      }}
                      className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setCurrentDate(new Date());
                          setShowDatePicker(false);
                        }}
                        className="text-xs"
                      >
                        Today
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowDatePicker(false)}
                        className="text-xs"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (viewMode === 'day') {
                  setCurrentDate(prev => addDaysUtility(prev, 1));
                } else if (viewMode === 'week') {
                  setCurrentDate(prev => addWeeks(prev, 1));
                } else {
                  setCurrentDate(prev => addMonths(prev, 1));
                }
              }}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="flex items-center gap-2">
            {/* View Mode Switcher */}
            <div className="flex items-center bg-slate-100 rounded-lg p-1">
              {(['month', 'week', 'day'] as const).map((mode) => (
                <Button
                  key={mode}
                  variant={viewMode === mode ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode(mode)}
                  className={cn(
                    "px-3 py-1 text-xs font-medium transition-colors",
                    viewMode === mode 
                      ? "bg-white shadow-sm" 
                      : "hover:bg-slate-200"
                  )}
                >
                  {mode.charAt(0).toUpperCase() + mode.slice(1)}
                </Button>
              ))}
            </div>
            
            {enableInteractions && (
              <Badge variant="secondary" className="text-xs">
                Interactive Mode
              </Badge>
            )}
            {showCloseButton && (
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleCloseWidget}
                className="bg-green-50 border-green-300 text-green-700 hover:bg-green-100"
              >
                ✓ Done Reviewing
              </Button>
            )}
          </div>
        </div>

        {/* Day Headers - Only show for month view */}
        {viewMode === 'month' && (
          <div className="grid grid-cols-7 mb-2">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
              <div key={day} className={cn(
                "text-center font-medium text-gray-500",
                compact ? "p-1 text-xs" : "p-2 text-sm"
              )}>
                {day}
              </div>
            ))}
          </div>
        )}

        {/* Calendar Grid */}
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          {renderCalendarGrid()}
        </div>
      </Card>

      {/* Event Detail Panel */}
      {selectedEvent && renderEventDetail()}
    </div>
  );
}