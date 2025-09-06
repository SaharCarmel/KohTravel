# Show Suggested Events Carousel Tool

## Purpose
Display all pending suggested events in the interactive calendar widget for user review and approval.

## When to Use

✅ **Use when**:
- User asks to see suggestions: "Show me the suggestions" 
- User wants to review pending events: "What events are waiting for approval?"
- After creating multiple suggestions: "Here are your options to review"
- User finishes providing feedback and wants to see what's available

❌ **Don't use**:
- To create new suggestions (use `suggest_calendar_event` instead)
- If no suggestions exist (create some first)
- For confirmed/existing events (use `get_calendar_events`)

## How It Works

This tool:
1. Counts all calendar events with `status="suggested"`  
2. Triggers the interactive calendar widget to appear in the chat
3. Shows only suggested events for user approval/rejection
4. Provides approve/reject buttons with feedback options

## No Parameters Required

This tool takes no parameters - it automatically shows all pending suggestions.

## Usage Flow

```
1. suggest_calendar_event() // Create suggestions first
2. suggest_calendar_event() // Maybe create more
3. show_suggested_events_carousel() // Then show them all for review
```

## Communication Style

After using this tool, explain what the user will see:
- "I've created X suggestions for your review"
- "You can now approve, reject, or provide feedback on each suggestion" 
- "Take your time reviewing - you can navigate between suggestions and add comments"
- "Once you're done reviewing, click 'Done Reviewing' to send me your feedback"

## User Experience

The carousel shows:
- **Event details**: Title, time, location, description
- **AI reasoning**: Why you suggested this event  
- **Confidence score**: Your confidence level (1-10)
- **Navigation**: Previous/Next buttons to browse suggestions
- **Actions**: Approve, reject, or provide detailed feedback
- **Progress**: "2 of 5 suggestions" indicator

## Best Practices

- Only use after creating meaningful suggestions
- Explain the review process to users
- Mention they can provide detailed feedback for better future suggestions
- Let them know approved events will be added to their calendar

## Example Usage

```
User: "Show me those restaurant suggestions"

1. show_suggested_events_carousel()
2. Response: "I've displayed 3 restaurant suggestions in the calendar widget above. You can review each one, see why I suggested it, and approve the ones you like. Navigate between them using the Previous/Next buttons, and click 'Done Reviewing' when finished to send me your feedback!"
```