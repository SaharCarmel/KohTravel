# Get Document Categories - Step 0 of Search Funnel

## Essential First Step

**ALWAYS start with this tool** to understand what types of documents the user has before searching.

## When to Use
- **Before any search** - use this to see what document types exist
- **For unfamiliar questions** - when you're not sure what type of document contains the answer
- **To guide search strategy** - knowing categories helps you search effectively

## What This Provides
- List of all document categories with counts
- Understanding of document portfolio structure  
- Guidance for targeted searching

## Universal Workflow
1. **First**: `get_document_categories()` → see what types exist
2. **Then**: `search_documents(category="relevant_category")` → filter by type
3. **Finally**: `get_document` → get specific details

## Example Flow
User asks: "What's the cancellation policy?"

1. `get_document_categories()` → see available types
2. If you see "Legal Policy" or "Terms and Conditions" → search those
3. If only "Other" exists → search with "cancel" or "policy"

## No Parameters Required
This tool takes no parameters - just call it to get the overview.

## Natural Flow
- "Let me see what types of documents you have..."
- "I'll check what categories are available..."
- "Let me understand your document portfolio first..."

**Use this tool FIRST for every travel question to understand the document landscape.**