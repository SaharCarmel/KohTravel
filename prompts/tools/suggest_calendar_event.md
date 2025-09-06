# Suggest Calendar Event Tool

## Purpose
Suggest new calendar events for user review and approval. Events appear in the interactive calendar widget for the user to approve or reject.

## MANDATORY Pre-Suggestion Workflow

**CRITICAL**: Before suggesting ANY calendar event, you MUST ALWAYS check the user's existing schedule to:
1. Avoid scheduling conflicts
2. Optimize timing based on existing events
3. Consider travel time between locations
4. Respect user's daily schedule patterns

### Required Steps Before Every Suggestion:

1. **Check Current Schedule**: Use `get_calendar_events()` to retrieve existing events for the target date(s)
2. **Analyze Timing**: Look for:
   - Existing events at or near your proposed time
   - Transportation/travel time between locations  
   - Meal times and break periods
   - Logical scheduling (don't suggest dinner at 10am)
3. **Find Optimal Slots**: Identify free time periods that make sense

## When to Use This Tool

✅ **Use when**:
- User asks for activity/restaurant/experience suggestions
- You want to propose events based on document analysis
- User needs schedule optimization
- You're helping plan daily itineraries

❌ **Don't use for**:
- Events that already exist in documents (use `create_calendar_event` instead)
- Updating existing events (use `update_calendar_event`)
- Just showing existing suggestions (use `show_suggested_events_carousel`)

## Parameters

- **title** (required): Clear, descriptive event name
- **start_datetime** (required): ISO format datetime (YYYY-MM-DDTHH:MM:SS)
- **end_datetime** (optional): ISO format datetime  
- **event_type** (required): flight | accommodation | activity | transport | dining | wellness
- **location** (optional): Specific address or venue name
- **description** (optional): Details about the event
- **all_day** (optional): Boolean, default false
- **suggestion_reason** (required): Brief explanation of why you're suggesting this
- **suggestion_confidence** (required): 1-10 scale of how confident you are this fits the user

## Best Practices

### Smart Scheduling
- **Morning activities**: 9am-12pm (after breakfast, before lunch)
- **Afternoon activities**: 2pm-5pm (after lunch, before dinner)  
- **Evening dining**: 6pm-9pm
- **Buffer time**: Leave 30-60min between events for travel

### Location Awareness  
- Group nearby activities together
- Consider transportation time between venues
- Suggest logical geographic flow

### User Context
- Reference user's travel documents when relevant
- Align with their interests shown in existing bookings
- Consider their travel style (luxury/budget, active/relaxed)

## Example Workflow

```
User: "What should we do tomorrow afternoon?"

1. get_calendar_events() // Check existing schedule for tomorrow
   → See: 9am Beach Walk, 12pm Lunch at Market, 6pm Dinner reservation

2. Analysis: Free time 2pm-5:30pm, near Tel Aviv center

3. suggest_calendar_event({
     title: "Visit Design Museum Holon", 
     start_datetime: "2025-09-07T14:00:00",
     end_datetime: "2025-09-07T16:00:00",
     event_type: "activity",
     location: "Design Museum Holon, Israel",
     suggestion_reason: "Perfect timing between lunch and dinner, fits your interest in museums from previous bookings",
     suggestion_confidence: 8
   })
```

## Communication Style

- Explain your scheduling logic naturally: "I noticed you have lunch at noon and dinner at 6, so the 2-4pm slot would be perfect for..."
- Reference existing schedule: "Since you're already at the market for lunch, this museum is just 20 minutes away"
- Be transparent about conflicts: "I see you have an early flight, so I'll suggest something close to the airport"

Remember: A good travel agent never double-books or ignores existing plans. Always check the calendar first!