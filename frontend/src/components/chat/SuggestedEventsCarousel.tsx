"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import { ChevronLeft, ChevronRight, Check, X, Calendar, MapPin, Clock, Lightbulb, Star, MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { calendarAPI, type CalendarEvent } from "@/lib/calendar-api";

interface SuggestedEventsCarouselProps {
  suggestedEvents: CalendarEvent[];
  onEventApproved: (eventId: string, approvedEvent: CalendarEvent) => void;
  onEventRejected: (eventId: string, feedback?: string) => void;
  onEventsUpdated: () => void;
}

const getEventTypeIcon = (eventType: string) => {
  const icons: Record<string, React.ReactNode> = {
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

export function SuggestedEventsCarousel({ 
  suggestedEvents, 
  onEventApproved, 
  onEventRejected, 
  onEventsUpdated 
}: SuggestedEventsCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [showFeedbackForm, setShowFeedbackForm] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [approvedEventIds, setApprovedEventIds] = useState<Set<string>>(new Set());

  const currentEvent = suggestedEvents[currentIndex];
  const isCurrentEventApproved = approvedEventIds.has(currentEvent?.id || '');

  const nextEvent = () => {
    setCurrentIndex((prev) => (prev + 1) % suggestedEvents.length);
    setShowFeedbackForm(false);
    setFeedback("");
  };

  const prevEvent = () => {
    setCurrentIndex((prev) => (prev - 1 + suggestedEvents.length) % suggestedEvents.length);
    setShowFeedbackForm(false);
    setFeedback("");
  };

  // Reset approved events when suggestions change
  useEffect(() => {
    setApprovedEventIds(new Set());
    setCurrentIndex(0);
  }, [suggestedEvents]);

  const handleApprove = async () => {
    if (!currentEvent) return;
    
    setIsApproving(true);
    try {
      const approvedEvent = await calendarAPI.approveEvent(currentEvent.id, {
        approved: true,
        user_feedback: "Approved from chat carousel"
      });
      
      // Mark this event as approved locally
      setApprovedEventIds(prev => new Set([...prev, currentEvent.id]));
      
      onEventApproved(currentEvent.id, approvedEvent);
      // DON'T call onEventsUpdated() - it refetches and removes approved events from carousel
      
      // DON'T auto-advance - let user manually navigate to see all suggestions
      // User can manually click next/prev to review remaining suggestions
    } catch (error) {
      console.error('Failed to approve event:', error);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async (withFeedback = false) => {
    if (!currentEvent) return;

    if (withFeedback && !feedback.trim()) {
      setShowFeedbackForm(true);
      return;
    }

    setIsRejecting(true);
    try {
      await calendarAPI.approveEvent(currentEvent.id, {
        approved: false,
        user_feedback: withFeedback ? feedback : "Rejected from chat carousel"
      });

      onEventRejected(currentEvent.id, withFeedback ? feedback : undefined);
      // DON'T call onEventsUpdated() - keeps carousel stable

      // DON'T auto-advance - let user manually navigate  
      setShowFeedbackForm(false);
      setFeedback("");
    } catch (error) {
      console.error('Failed to reject event:', error);
    } finally {
      setIsRejecting(false);
    }
  };

  if (!suggestedEvents.length || !currentEvent) {
    return null;
  }

  return (
    <Card className="w-full max-w-md mx-auto bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-amber-500" />
            <CardTitle className="text-lg font-semibold text-slate-900">
              Suggested Event
            </CardTitle>
          </div>
          {suggestedEvents.length > 1 && (
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={prevEvent}
                className="h-8 w-8 p-0"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-slate-600 px-2">
                {currentIndex + 1}/{suggestedEvents.length}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={nextEvent}
                className="h-8 w-8 p-0"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
        
        {currentEvent.suggestion_confidence && (
          <div className="flex items-center gap-2 mt-2">
            <Badge 
              variant="secondary" 
              className={cn("text-xs font-medium", getConfidenceColor(currentEvent.suggestion_confidence))}
            >
              <Star className="h-3 w-3 mr-1" />
              {currentEvent.suggestion_confidence}/10 confidence
            </Badge>
            <Badge variant="outline" className="text-xs">
              {currentEvent.suggested_by || 'agent'}
            </Badge>
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Event Details */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="text-2xl">
              {getEventTypeIcon(currentEvent.event_type)}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-slate-900 leading-tight">
                {currentEvent.title}
              </h3>
              {currentEvent.description && (
                <p className="text-sm text-slate-600 mt-1">
                  {currentEvent.description}
                </p>
              )}
            </div>
          </div>

          {/* Time & Location */}
          <div className="space-y-2 pl-11">
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Calendar className="h-4 w-4" />
              {format(new Date(currentEvent.start_datetime), "MMM dd, yyyy")}
            </div>
            
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Clock className="h-4 w-4" />
              {currentEvent.all_day ? (
                "All day"
              ) : (
                <>
                  {format(new Date(currentEvent.start_datetime), "h:mm a")}
                  {currentEvent.end_datetime && 
                    ` - ${format(new Date(currentEvent.end_datetime), "h:mm a")}`
                  }
                </>
              )}
            </div>

            {currentEvent.location && (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <MapPin className="h-4 w-4" />
                {currentEvent.location}
              </div>
            )}
          </div>

          {/* AI Reasoning */}
          {currentEvent.suggestion_reason && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <MessageCircle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-xs font-medium text-amber-800 mb-1">
                    Why I suggested this:
                  </p>
                  <p className="text-sm text-amber-700">
                    {currentEvent.suggestion_reason}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Feedback Form */}
        {showFeedbackForm && (
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-slate-700 mb-2 block">
                Tell me why this doesn't work for you:
              </label>
              <Textarea
                placeholder="e.g., I prefer morning flights, or I already have plans that day..."
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                className="text-sm"
                rows={3}
              />
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-2">
          <Button
            onClick={handleApprove}
            disabled={isApproving || isRejecting || isCurrentEventApproved}
            className={cn(
              "flex-1 text-white",
              isCurrentEventApproved 
                ? "bg-green-800 hover:bg-green-800 cursor-default" 
                : "bg-green-600 hover:bg-green-700"
            )}
          >
            {isApproving ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Adding...
              </div>
            ) : isCurrentEventApproved ? (
              <>
                <Check className="h-4 w-4 mr-2" />
                Added ✓
              </>
            ) : (
              <>
                <Check className="h-4 w-4 mr-2" />
                Add to Calendar
              </>
            )}
          </Button>
          
          {showFeedbackForm ? (
            <>
              <Button
                onClick={() => handleReject(true)}
                disabled={isApproving || isRejecting || !feedback.trim()}
                variant="outline"
                className="border-red-200 text-red-700 hover:bg-red-50"
              >
                {isRejecting ? "..." : "Submit"}
              </Button>
              <Button
                onClick={() => {
                  setShowFeedbackForm(false);
                  setFeedback("");
                }}
                variant="ghost"
                size="sm"
                className="text-slate-500"
              >
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button
                onClick={() => handleReject(false)}
                disabled={isApproving || isRejecting}
                variant="outline"
                className="border-red-200 text-red-700 hover:bg-red-50"
              >
                <X className="h-4 w-4 mr-1" />
                Skip
              </Button>
              <Button
                onClick={() => setShowFeedbackForm(true)}
                disabled={isApproving || isRejecting}
                variant="ghost"
                size="sm"
                className="text-slate-600 hover:text-slate-800"
              >
                <MessageCircle className="h-4 w-4" />
              </Button>
            </>
          )}
        </div>

        {/* Progress Indicators */}
        {suggestedEvents.length > 1 && (
          <div className="flex justify-center gap-1 pt-2">
            {suggestedEvents.map((_, index) => (
              <div
                key={index}
                className={cn(
                  "w-2 h-2 rounded-full transition-colors",
                  index === currentIndex ? "bg-blue-500" : "bg-slate-300"
                )}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}