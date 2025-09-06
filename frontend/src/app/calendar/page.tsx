"use client";

import { Calendar } from "@/components/calendar/Calendar";

export default function CalendarPage() {
  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Trip Calendar</h1>
            <p className="text-muted-foreground">
              View and manage your travel itinerary
            </p>
          </div>
        </div>
        <Calendar />
      </div>
    </div>
  );
}