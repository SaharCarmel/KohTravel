# KohTravel MVP - Complete Task Breakdown

## 🎯 **Project Overview**
Travel document management app with AI-powered chat interface. Users upload travel documents (invoices, flight details, tourist info), and chat to ask questions about their trip details.

## 🏗️ **Architecture Decisions**
- **Frontend**: Next.js + TypeScript + Tailwind CSS + shadcn/ui
- **Backend**: FastAPI + Python (Vercel Serverless Functions)
- **Database**: PostgreSQL (Railway) + Alembic migrations
- **AI**: Claude 4 Sonnet for document processing and chat
- **Auth**: Vercel Auth (Google + GitHub)
- **File Processing**: Docling + OCR (extract text, discard files)
- **Real-time**: Server-Sent Events (SSE) for processing updates
- **Deployment**: Vercel with auto-deploy from GitHub

## 🗄️ **Database Schema**
```sql
-- Users (linked to Vercel Auth)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  vercel_user_id VARCHAR(255) UNIQUE NOT NULL,
  email VARCHAR(255),
  name VARCHAR(255),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Document Categories (expandable)
CREATE TABLE document_categories (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  keywords TEXT[],
  extraction_fields JSON,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Documents (no file storage, text only)
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id),
  category_id INTEGER REFERENCES document_categories(id),
  title VARCHAR(255) NOT NULL,
  original_filename VARCHAR(255),
  raw_text TEXT,
  summary TEXT,
  structured_data JSON,
  processing_status VARCHAR(50) DEFAULT 'pending',
  confidence_score FLOAT,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Quick reference fields for fast queries
CREATE TABLE document_quick_refs (
  id SERIAL PRIMARY KEY,
  document_id UUID REFERENCES documents(id),
  field_name VARCHAR(100),
  field_value TEXT,
  field_type VARCHAR(50)
);

-- Indexes for performance
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_category ON documents(category_id);
CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_quick_refs_document ON document_quick_refs(document_id);
CREATE INDEX idx_quick_refs_field ON document_quick_refs(field_name);
```

---

# 📋 **PHASE BREAKDOWN**

## **PHASE 1: Foundation & Infrastructure**
*Goal: Set up core infrastructure and basic app structure*

### 1.1 Database Setup
- [ ] **1.1.1** Create Railway PostgreSQL database
- [ ] **1.1.2** Configure connection string in Vercel environment
- [ ] **1.1.3** Add database dependencies (`uv add sqlalchemy alembic psycopg2-binary`)
- [ ] **1.1.4** Initialize Alembic in `/api` directory
- [ ] **1.1.5** Create initial database models (SQLAlchemy)
- [ ] **1.1.6** Set up auto-migration on startup
- [ ] **1.1.7** Create seed data for document categories

### 1.2 Authentication Setup  
- [ ] **1.2.1** Configure Vercel Auth with Google & GitHub providers
- [ ] **1.2.2** Set up auth environment variables
- [ ] **1.2.3** Create user registration/login flow
- [ ] **1.2.4** Implement user session management
- [ ] **1.2.5** Add protected API routes middleware
- [ ] **1.2.6** Create user profile page

### 1.3 Basic UI Structure
- [ ] **1.3.1** Create main dashboard layout
- [ ] **1.3.2** Add navigation components
- [ ] **1.3.3** Set up routing structure
- [ ] **1.3.4** Add loading states and error boundaries
- [ ] **1.3.5** Implement responsive design basics

---

## **PHASE 2: Document Upload & Processing**
*Goal: Core document handling functionality*

### 2.1 File Upload System
- [ ] **2.1.1** Design drag & drop upload UI component
- [ ] **2.1.2** Implement file validation (PDF only, 4.5MB limit)
- [ ] **2.1.3** Create upload progress indicators
- [ ] **2.1.4** Add file preview capabilities
- [ ] **2.1.5** Handle upload errors gracefully

### 2.2 Document Processing Pipeline
- [ ] **2.2.1** Add Docling dependencies (`uv add docling`)
- [ ] **2.2.2** Create document parsing service
- [ ] **2.2.3** Implement OCR text extraction
- [ ] **2.2.4** Set up background processing workflow
- [ ] **2.2.5** Create processing status tracking
- [ ] **2.2.6** Add error handling and retry logic

### 2.3 AI Integration (Claude)
- [ ] **2.3.1** Set up Claude SDK (`uv add anthropic`)
- [ ] **2.3.2** Design document classification prompts
- [ ] **2.3.3** Create structured data extraction prompts
- [ ] **2.3.4** Implement AI service layer
- [ ] **2.3.5** Add fallback error handling
- [ ] **2.3.6** Test with sample documents

### 2.4 Real-time Updates
- [ ] **2.4.1** Implement Server-Sent Events (SSE) endpoint
- [ ] **2.4.2** Create real-time status updates for processing
- [ ] **2.4.3** Add frontend SSE connection handling
- [ ] **2.4.4** Show live processing progress to users
- [ ] **2.4.5** Handle connection failures gracefully

---

## **PHASE 3: Document Management & Viewing**
*Goal: Document organization and basic viewing*

### 3.1 Document List & Organization
- [ ] **3.1.1** Create documents list page
- [ ] **3.1.2** Add document filtering by category
- [ ] **3.1.3** Implement basic search functionality
- [ ] **3.1.4** Add sorting options (date, category, status)
- [ ] **3.1.5** Create document card components

### 3.2 Document Viewer
- [ ] **3.2.1** Design minimal document viewer UI
- [ ] **3.2.2** Display extracted text content
- [ ] **3.2.3** Show structured data fields
- [ ] **3.2.4** Add document summary display
- [ ] **3.2.5** Create edit/update functionality for metadata

### 3.3 Document Actions
- [ ] **3.3.1** Add document deletion functionality  
- [ ] **3.3.2** Implement reprocess document option
- [ ] **3.3.3** Create document sharing capabilities
- [ ] **3.3.4** Add bulk operations (select multiple)

---

## **PHASE 4: Chat Interface & AI Agent**
*Goal: Intelligent chat system for document queries*

### 4.1 Chat UI Components
- [ ] **4.1.1** Design chat interface layout
- [ ] **4.1.2** Create message bubble components
- [ ] **4.1.3** Add typing indicators
- [ ] **4.1.4** Implement message input with file upload
- [ ] **4.1.5** Add suggested questions feature
- [ ] **4.1.6** Create chat history display (session-based)

### 4.2 AI Agent Implementation
- [ ] **4.2.1** Design system prompts for travel assistant
- [ ] **4.2.2** Create context injection system (user documents)
- [ ] **4.2.3** Implement SQL query generation for document search
- [ ] **4.2.4** Add response streaming with SSE
- [ ] **4.2.5** Create fallback responses for edge cases
- [ ] **4.2.6** Add conversation context management

### 4.3 Chat Functionality
- [ ] **4.3.1** Process user questions about documents
- [ ] **4.3.2** Generate intelligent responses with document references
- [ ] **4.3.3** Handle follow-up questions
- [ ] **4.3.4** Add document upload via chat
- [ ] **4.3.5** Implement error handling for failed queries

---

## **PHASE 5: Polish & Security**
*Goal: Production-ready features and security*

### 5.1 Security Implementation
- [ ] **5.1.1** Add input validation and sanitization
- [ ] **5.1.2** Implement rate limiting for API endpoints
- [ ] **5.1.3** Add CSRF protection
- [ ] **5.1.4** Set up proper error logging (without sensitive data)
- [ ] **5.1.5** Implement user data privacy controls
- [ ] **5.1.6** Add basic GDPR compliance features

### 5.2 Performance Optimization
- [ ] **5.2.1** Add database query optimization
- [ ] **5.2.2** Implement lazy loading for document lists
- [ ] **5.2.3** Optimize bundle size and loading performance
- [ ] **5.2.4** Add service worker for offline functionality
- [ ] **5.2.5** Monitor and optimize API response times

### 5.3 User Experience Polish
- [ ] **5.3.1** Add comprehensive loading states
- [ ] **5.3.2** Improve error messages and user feedback
- [ ] **5.3.3** Add onboarding flow for new users
- [ ] **5.3.4** Implement keyboard shortcuts
- [ ] **5.3.5** Add dark mode support
- [ ] **5.3.6** Optimize for mobile (if time permits)

---

## **PHASE 6: Testing & Deployment**
*Goal: Production deployment and testing*

### 6.1 Testing
- [ ] **6.1.1** Add unit tests for core functions
- [ ] **6.1.2** Create integration tests for document processing
- [ ] **6.1.3** Add end-to-end tests for user flows
- [ ] **6.1.4** Test with various document types and sizes
- [ ] **6.1.5** Performance testing under load

### 6.2 Production Deployment
- [ ] **6.2.1** Set up production database on Railway
- [ ] **6.2.2** Configure production environment variables
- [ ] **6.2.3** Set up monitoring and logging
- [ ] **6.2.4** Create backup and recovery procedures
- [ ] **6.2.5** Deploy to production and test

### 6.3 Documentation & Maintenance
- [ ] **6.3.1** Create user documentation/help
- [ ] **6.3.2** Document API endpoints
- [ ] **6.3.3** Set up basic analytics
- [ ] **6.3.4** Create maintenance procedures
- [ ] **6.3.5** Plan post-MVP features roadmap

---

## 🚀 **Immediate Next Steps**
1. Start with **Phase 1.1** - Database Setup
2. Move to **Phase 1.2** - Authentication Setup  
3. Begin **Phase 2.1** - File Upload System

---

# 🧪 **TESTING CRITERIA BY PHASE**

## **PHASE 1: Foundation & Infrastructure**
### Programmatic Tests:
- [ ] Database connection successful
- [ ] Alembic migrations run without errors
- [ ] User registration/login API endpoints work
- [ ] Protected routes require authentication
- [ ] Environment variables loaded correctly

### Manual Testing:
- [ ] Can create account with Google/GitHub
- [ ] Dashboard loads after login
- [ ] Logout works properly
- [ ] Responsive layout on different screen sizes
- [ ] Error pages display correctly

### Definition of Done:
- User can sign up, log in, and see empty dashboard

---

## **PHASE 2: Document Upload & Processing**
### Programmatic Tests:
- [ ] File upload validation (PDF only, size limits)
- [ ] Docling text extraction works
- [ ] Claude API integration functional
- [ ] Document records saved to database
- [ ] Processing status updates correctly

### Manual Testing:
- [ ] Drag & drop file upload works
- [ ] Progress indicators show during processing
- [ ] Success/error notifications display
- [ ] Can upload sample PDF and see extracted text
- [ ] Processing errors handled gracefully

### Definition of Done:
- User can upload PDF, see processing progress, and view extracted document data

---

## **PHASE 3: Document Management & Viewing**
### Programmatic Tests:
- [ ] Document list API returns user's documents
- [ ] Filtering and sorting work correctly
- [ ] Document deletion removes from database
- [ ] Document viewer displays all fields

### Manual Testing:
- [ ] Documents list shows all uploaded files
- [ ] Can filter by category and date
- [ ] Document viewer shows text and structured data
- [ ] Delete document works with confirmation
- [ ] Empty states display properly

### Definition of Done:
- User can view, organize, and manage their uploaded documents

---

## **PHASE 4: Chat Interface & AI Agent**
### Programmatic Tests:
- [ ] Chat API accepts messages and returns responses
- [ ] SQL queries generated correctly for document search
- [ ] SSE connection established for streaming
- [ ] Message validation and sanitization

### Manual Testing:
- [ ] Can type and send messages in chat
- [ ] AI responds with relevant document information
- [ ] Can ask questions about specific documents
- [ ] Streaming responses work smoothly
- [ ] File upload through chat functions

### Definition of Done:
- User can chat with AI about their documents and get accurate answers

---

## **PHASE 5: Polish & Security**
### Programmatic Tests:
- [ ] Rate limiting blocks excessive requests
- [ ] Input validation prevents SQL injection
- [ ] Error logging works without exposing secrets
- [ ] Performance benchmarks meet targets

### Manual Testing:
- [ ] App feels fast and responsive
- [ ] Error messages are helpful and clear
- [ ] Loading states provide good feedback
- [ ] Security features don't break user experience

### Definition of Done:
- App is secure, performant, and provides excellent user experience

---

## **PHASE 6: Testing & Deployment**
### Programmatic Tests:
- [ ] Full test suite passes
- [ ] Production build successful
- [ ] Database migrations work in production
- [ ] All environment variables configured

### Manual Testing:
- [ ] End-to-end user journey works flawlessly
- [ ] Production deployment accessible
- [ ] All features work in production environment
- [ ] Performance acceptable under realistic load

### Definition of Done:
- MVP is live in production and ready for real users

## ⏱️ **Estimated Timeline**
- **Phase 1**: 1-2 weeks
- **Phase 2**: 2-3 weeks  
- **Phase 3**: 1-2 weeks
- **Phase 4**: 2-3 weeks
- **Phase 5**: 1-2 weeks
- **Phase 6**: 1 week

**Total MVP Estimate**: 8-13 weeks