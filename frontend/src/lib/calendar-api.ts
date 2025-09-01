import { apiClient } from './api-client'

// Types matching the backend API
export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  location?: string;
  start_datetime: string; // ISO string
  end_datetime?: string;
  all_day: boolean;
  event_type: 'flight' | 'accommodation' | 'activity' | 'transport' | 'dining' | 'wellness';
  color?: string;
  status: 'confirmed' | 'tentative' | 'cancelled';
  notes?: string;
  source: string;
  document_id?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateEventData {
  title: string;
  description?: string;
  location?: string;
  start_datetime: string;
  end_datetime?: string;
  all_day?: boolean;
  event_type: 'flight' | 'accommodation' | 'activity' | 'transport' | 'dining' | 'wellness';
  color?: string;
  status?: 'confirmed' | 'tentative' | 'cancelled';
  notes?: string;
  document_id?: string;
}

export interface UpdateEventData extends Partial<CreateEventData> {}

export interface EventType {
  type: string;
  label: string;
  color: string;
}

class CalendarAPI {
  async getEvents(params?: {
    start_date?: string;
    end_date?: string;
    event_type?: string;
  }): Promise<CalendarEvent[]> {
    const query = new URLSearchParams(
      Object.entries(params || {}).filter(([_, value]) => value !== undefined) as [string, string][]
    );
    
    return apiClient.get<CalendarEvent[]>(`/api/calendar/events?${query}`);
  }

  async getEvent(id: string): Promise<CalendarEvent> {
    return apiClient.get<CalendarEvent>(`/api/calendar/events/${id}`);
  }

  async createEvent(data: CreateEventData): Promise<CalendarEvent> {
    return apiClient.post<CalendarEvent>(`/api/calendar/events`, data);
  }

  async updateEvent(id: string, data: UpdateEventData): Promise<CalendarEvent> {
    return apiClient.put<CalendarEvent>(`/api/calendar/events/${id}`, data);
  }

  async deleteEvent(id: string): Promise<{ success: boolean }> {
    return apiClient.delete<{ success: boolean }>(`/api/calendar/events/${id}`);
  }

  async getEventTypes(): Promise<EventType[]> {
    return apiClient.get<EventType[]>(`/api/calendar/event-types`);
  }

  async getStats(params?: {
    start_date?: string;
    end_date?: string;
  }): Promise<any> {
    const query = new URLSearchParams(
      Object.entries(params || {}).filter(([_, value]) => value !== undefined) as [string, string][]
    );
    
    return apiClient.get(`/api/calendar/stats?${query}`);
  }
}

export const calendarAPI = new CalendarAPI();