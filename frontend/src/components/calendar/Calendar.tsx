"use client";

import { useState } from "react";
import { format, startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, isSameMonth, isSameDay, isToday, startOfDay, endOfDay, addWeeks, subWeeks, addMonths, subMonths, eachHourOfInterval, startOfHour } from "date-fns";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Mock trip events data - Thailand Adventure Trip
const mockEvents = [
  {
    id: 1,
    title: "Flight to Bangkok",
    date: new Date(2025, 7, 30), // August 30, 2025
    time: "08:30",
    type: "flight",
    color: "bg-blue-500",
    description: "TG 123 - Don Mueang Airport"
  },
  {
    id: 2,
    title: "Hotel Check-in",
    date: new Date(2025, 7, 30),
    time: "15:00",
    type: "accommodation",
    color: "bg-green-500",
    description: "Chatrium Hotel Riverside"
  },
  {
    id: 3,
    title: "Temple Tour",
    date: new Date(2025, 7, 31),
    time: "09:00",
    type: "activity",
    color: "bg-purple-500",
    description: "Wat Pho & Grand Palace"
  },
  {
    id: 4,
    title: "Cooking Class",
    date: new Date(2025, 8, 1), // September 1, 2025
    time: "14:00",
    type: "activity",
    color: "bg-orange-500",
    description: "Thai Cooking Academy"
  },
  {
    id: 5,
    title: "Ferry to Koh Samui",
    date: new Date(2025, 8, 2),
    time: "07:00",
    type: "transport",
    color: "bg-cyan-500",
    description: "Lomprayah High Speed Ferry"
  },
  {
    id: 6,
    title: "Beach Resort Check-in",
    date: new Date(2025, 8, 2),
    time: "14:00",
    type: "accommodation",
    color: "bg-green-500",
    description: "Four Seasons Koh Samui"
  },
  {
    id: 7,
    title: "Snorkeling Trip",
    date: new Date(2025, 8, 4),
    time: "08:30",
    type: "activity",
    color: "bg-blue-400",
    description: "Angthong Marine Park"
  },
  {
    id: 8,
    title: "Spa Appointment",
    date: new Date(2025, 8, 5),
    time: "16:00",
    type: "wellness",
    color: "bg-pink-500",
    description: "Traditional Thai Massage"
  },
  {
    id: 9,
    title: "Flight to Phuket",
    date: new Date(2025, 8, 6),
    time: "11:00",
    type: "flight",
    color: "bg-blue-500",
    description: "Bangkok Airways PG 145"
  },
  {
    id: 10,
    title: "Sunset Dinner",
    date: new Date(2025, 8, 7),
    time: "18:30",
    type: "dining",
    color: "bg-yellow-500",
    description: "Mom Tri's Kitchen"
  }
];

type Event = typeof mockEvents[0];
type ViewMode = 'month' | 'week' | 'day';

export function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('month');

  // Get events for a specific date
  const getEventsForDate = (date: Date): Event[] => {
    return mockEvents.filter(event => isSameDay(event.date, date));
  };

  // Navigate dates based on view mode
  const goToPrevious = () => {
    if (viewMode === 'month') {
      setCurrentDate(prev => subMonths(prev, 1));
    } else if (viewMode === 'week') {
      setCurrentDate(prev => subWeeks(prev, 1));
    } else {
      setCurrentDate(prev => addDays(prev, -1));
    }
  };

  const goToNext = () => {
    if (viewMode === 'month') {
      setCurrentDate(prev => addMonths(prev, 1));
    } else if (viewMode === 'week') {
      setCurrentDate(prev => addWeeks(prev, 1));
    } else {
      setCurrentDate(prev => addDays(prev, 1));
    }
  };

  // Get current view title
  const getViewTitle = () => {
    if (viewMode === 'month') {
      return format(currentDate, "MMMM yyyy");
    } else if (viewMode === 'week') {
      const weekStart = startOfWeek(currentDate);
      const weekEnd = endOfWeek(currentDate);
      return `${format(weekStart, "MMM d")} - ${format(weekEnd, "MMM d, yyyy")}`;
    } else {
      return format(currentDate, "EEEE, MMMM d, yyyy");
    }
  };

  // Render month view
  const renderMonthView = () => {
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(monthStart);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);
    
    const dateFormat = "d";
    const rows = [];
    let days = [];
    let day = startDate;

    while (day <= endDate) {
      for (let i = 0; i < 7; i++) {
        const dayEvents = getEventsForDate(day);
        const isCurrentMonth = isSameMonth(day, monthStart);
        const isSelected = selectedDate && isSameDay(day, selectedDate);
        const isTodayDate = isToday(day);
        
        days.push(
          <div
            key={day.toString()}
            className={cn(
              "min-h-32 p-1 border border-gray-200 cursor-pointer transition-colors",
              !isCurrentMonth && "bg-gray-50 text-gray-400",
              isSelected && "bg-blue-50 border-blue-300",
              isTodayDate && "bg-yellow-50 border-yellow-300",
              "hover:bg-gray-50"
            )}
            onClick={() => setSelectedDate(day)}
          >
            <div className="flex justify-between items-start mb-1">
              <span className={cn(
                "text-sm font-medium",
                isTodayDate && "text-yellow-600 font-bold",
                !isCurrentMonth && "text-gray-400"
              )}>
                {format(day, dateFormat)}
              </span>
              {dayEvents.length > 0 && (
                <Badge variant="secondary" className="text-xs px-1 py-0">
                  {dayEvents.length}
                </Badge>
              )}
            </div>
            <div className="space-y-1">
              {dayEvents.slice(0, 3).map((event) => (
                <div
                  key={event.id}
                  className={cn(
                    "text-xs p-1 rounded text-white truncate",
                    event.color
                  )}
                  title={`${event.time} - ${event.title}`}
                >
                  {event.time} {event.title}
                </div>
              ))}
              {dayEvents.length > 3 && (
                <div className="text-xs text-gray-500 font-medium">
                  +{dayEvents.length - 3} more
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

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        {rows}
      </div>
    );
  };

  // Render week view
  const renderWeekView = () => {
    const weekStart = startOfWeek(currentDate);
    const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="grid grid-cols-7 border-b">
          {weekDays.map((day) => {
            const dayEvents = getEventsForDate(day);
            const isSelected = selectedDate && isSameDay(day, selectedDate);
            const isTodayDate = isToday(day);
            
            return (
              <div
                key={day.toString()}
                className={cn(
                  "min-h-96 p-2 border-r border-gray-200 cursor-pointer transition-colors",
                  isSelected && "bg-blue-50 border-blue-300",
                  isTodayDate && "bg-yellow-50",
                  "hover:bg-gray-50"
                )}
                onClick={() => setSelectedDate(day)}
              >
                <div className="text-center mb-2">
                  <div className="text-xs font-medium text-gray-500 uppercase">
                    {format(day, "EEE")}
                  </div>
                  <div className={cn(
                    "text-lg font-medium",
                    isTodayDate && "text-yellow-600 font-bold"
                  )}>
                    {format(day, "d")}
                  </div>
                  {dayEvents.length > 0 && (
                    <Badge variant="secondary" className="text-xs px-1 py-0 mt-1">
                      {dayEvents.length}
                    </Badge>
                  )}
                </div>
                <div className="space-y-1">
                  {dayEvents.map((event) => (
                    <div
                      key={event.id}
                      className={cn(
                        "text-xs p-2 rounded text-white",
                        event.color
                      )}
                      title={event.description}
                    >
                      <div className="font-medium">{event.time}</div>
                      <div className="truncate">{event.title}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // Render day view
  const renderDayView = () => {
    const hours = eachHourOfInterval({
      start: startOfDay(currentDate),
      end: endOfDay(currentDate)
    });

    const dayEvents = getEventsForDate(currentDate);

    return (
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="p-4 border-b bg-gray-50">
          <div className="text-center">
            <div className="text-sm font-medium text-gray-500 uppercase">
              {format(currentDate, "EEEE")}
            </div>
            <div className={cn(
              "text-2xl font-bold",
              isToday(currentDate) && "text-yellow-600"
            )}>
              {format(currentDate, "MMMM d, yyyy")}
            </div>
            {dayEvents.length > 0 && (
              <Badge variant="secondary" className="text-sm px-2 py-1 mt-2">
                {dayEvents.length} events
              </Badge>
            )}
          </div>
        </div>
        
        <div className="max-h-96 overflow-y-auto">
          {hours.map((hour) => {
            const hourEvents = dayEvents.filter(event => {
              const [eventHour] = event.time.split(':').map(Number);
              return eventHour === hour.getHours();
            });

            return (
              <div key={hour.toString()} className="flex border-b border-gray-100 min-h-16">
                <div className="w-20 p-2 text-right text-sm text-gray-500 border-r">
                  {format(hour, "HH:mm")}
                </div>
                <div className="flex-1 p-2">
                  <div className="space-y-1">
                    {hourEvents.map((event) => (
                      <div
                        key={event.id}
                        className={cn(
                          "p-2 rounded text-white",
                          event.color
                        )}
                      >
                        <div className="font-medium">{event.title}</div>
                        <div className="text-xs opacity-90">{event.description}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      {/* Calendar Header */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              size="sm"
              onClick={goToPrevious}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-xl font-semibold min-w-64 text-center">
              {getViewTitle()}
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={goToNext}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* View Mode Buttons */}
            <div className="flex border border-input rounded-md">
              <Button
                variant={viewMode === 'month' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-r-none border-r"
                onClick={() => setViewMode('month')}
              >
                Month
              </Button>
              <Button
                variant={viewMode === 'week' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-none border-r"
                onClick={() => setViewMode('week')}
              >
                Week
              </Button>
              <Button
                variant={viewMode === 'day' ? 'default' : 'ghost'}
                size="sm"
                className="rounded-l-none"
                onClick={() => setViewMode('day')}
              >
                Day
              </Button>
            </div>
            
            <Button size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Event
            </Button>
          </div>
        </div>

        {/* Day Headers for Month and Week View */}
        {(viewMode === 'month' || viewMode === 'week') && (
          <div className="grid grid-cols-7 mb-2">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
              <div key={day} className="p-2 text-center text-sm font-medium text-gray-500">
                {day}
              </div>
            ))}
          </div>
        )}

        {/* Calendar View */}
        {viewMode === 'month' && renderMonthView()}
        {viewMode === 'week' && renderWeekView()}
        {viewMode === 'day' && renderDayView()}
      </Card>

      {/* Event Details for Selected Date */}
      {selectedDate && (
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-3">
            Events for {format(selectedDate, "EEEE, MMMM d, yyyy")}
          </h3>
          {getEventsForDate(selectedDate).length === 0 ? (
            <p className="text-gray-500">No events scheduled for this day.</p>
          ) : (
            <div className="space-y-3">
              {getEventsForDate(selectedDate).map((event) => (
                <div key={event.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                  <div className={cn("w-3 h-3 rounded-full mt-1", event.color)} />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium">{event.title}</h4>
                      <span className="text-sm text-gray-500">{event.time}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{event.description}</p>
                    <Badge variant="outline" className="mt-2 text-xs">
                      {event.type}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Legend */}
      <Card className="p-4">
        <h3 className="text-sm font-medium mb-3">Event Types</h3>
        <div className="flex flex-wrap gap-3">
          {[
            { type: "flight", color: "bg-blue-500", label: "Flight" },
            { type: "accommodation", color: "bg-green-500", label: "Accommodation" },
            { type: "activity", color: "bg-purple-500", label: "Activity" },
            { type: "transport", color: "bg-cyan-500", label: "Transport" },
            { type: "dining", color: "bg-yellow-500", label: "Dining" },
            { type: "wellness", color: "bg-pink-500", label: "Wellness" }
          ].map(({ type, color, label }) => (
            <div key={type} className="flex items-center space-x-2">
              <div className={cn("w-3 h-3 rounded-full", color)} />
              <span className="text-sm">{label}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}