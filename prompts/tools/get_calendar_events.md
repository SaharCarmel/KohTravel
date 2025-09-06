# Get Calendar Events Tool

## Purpose
Retrieve the user's existing calendar events to understand their schedule before making suggestions or answering schedule-related questions.

## CRITICAL IMPORTANCE
This tool is MANDATORY before:
- Suggesting new calendar events
- Answering "what's my schedule" questions  
- Planning daily itineraries
- Checking for scheduling conflicts

Think like a real travel agent - you always check someone's existing bookings before suggesting new ones!

## When to Use

✅ **Always use before**:
- `suggest_calendar_event()` - Check existing schedule first
- Planning daily activities
- Answering schedule questions ("What's tomorrow look like?")
- Finding free time slots
- Checking for conflicts

✅ **Use when user asks**:
- "What's my schedule for tomorrow?"
- "What events do I have?"
- "Show me my calendar"
- "Am I free on Tuesday afternoon?"

## Parameters

- **start_date** (optional): Filter events from this date (YYYY-MM-DD format)  
- **end_date** (optional): Filter events until this date (YYYY-MM-DD format)
- **event_type** (optional): Filter by type (flight, accommodation, activity, transport, dining, wellness)

Leave parameters empty to get all events.

## Response Analysis

After getting calendar events, analyze:
- **Time gaps**: When is the user free?
- **Location patterns**: Where are they during the day?
- **Event types**: What kind of activities do they have?
- **Travel time**: How far apart are events?
- **Daily rhythm**: Meals, rest periods, activity levels

## Usage Examples

### Before Suggesting Events
```
User: "Suggest something fun for tomorrow"

1. get_calendar_events(start_date="2025-09-07", end_date="2025-09-07")
   → Returns: 10am Beach Walk, 1pm Lunch, 7pm Dinner

2. Analysis: Free 2pm-6pm, near beach area
3. suggest_calendar_event() for afternoon activity
```

### Schedule Questions
```  
User: "What's my schedule tomorrow?"

1. get_calendar_events(start_date="2025-09-07", end_date="2025-09-07") 
2. Present the schedule in a user-friendly format
```

### Finding Free Time
```
User: "When am I free this week?"

1. get_calendar_events(start_date="2025-09-07", end_date="2025-09-13")
2. Identify gaps between events and suggest optimal times
```

## Communication Style

Present calendar information naturally:
- "Let me see what you have planned..."
- "Looking at your schedule..."  
- "I can see you're free between 2pm and 6pm"
- "Since you have lunch nearby, this would work perfectly"

Don't say: "Executing calendar query" or "Retrieving events from database"

## Event Status Understanding

- **confirmed**: Definite bookings (flights, hotels, restaurants)
- **tentative**: Flexible plans 
- **suggested**: Events you've suggested that await approval
- **cancelled**: Cancelled events (usually hidden)

Focus on confirmed and tentative events when checking for conflicts.