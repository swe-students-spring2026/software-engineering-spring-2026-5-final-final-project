# AGENT.md

## 1. Project Overview

Project Name: AI Course Selection Assistant  
Type: Full-stack web application with AI-powered planning

This project is a web application that helps students plan their semester by combining:

- University course catalog data
- Section-level scheduling and enrollment data
- Graduation requirements
- User academic history

The system uses an AI agent to recommend optimal courses for the next semester based on constraints such as prerequisites, degree progress, and scheduling conflicts.

## 2. Core Features

### 2.1 Course Search
Users can:
- Search courses by name, subject, or keyword
- View:
  - Course description
  - Credits
  - Prerequisites
  - Department

### 2.2 Section-Level Details
Each course may have multiple sections. Each section includes:
- Section number
- Meeting days and times
- Location if available
- Enrollment status: Open / Closed / Waitlisted

### 2.3 AI Course Recommendation
Users provide:
- Completed courses
- Intended major

The AI:
- Determines fulfilled requirements
- Identifies missing requirements
- Validates prerequisites
- Avoids schedule conflicts
- Suggests best courses

### 2.4 Schedule Builder
- Add/remove course sections
- Detect time conflicts
- Generate weekly schedule
- Export schedule

### 2.5 Enrollment Status Refresh
Users can:
- View enrollment status
- Click refresh to trigger targeted scraping
- See updated status and timestamp

Constraints:
- Rate limited
- Section-level only
- Fallback on failure

## 3. System Architecture

### Frontend
Handles UI/UX and displays all data

### API Backend (Python)
Handles:
- Queries
- Recommendation logic
- Schedule validation
- Transcript parsing
- Refresh triggers

### Scraper Worker

Catalog Scraper:
- Uses NYU Bulletins API
- Runs daily

Section Scraper:
- On-demand
- Uses browser automation
- Collects meeting time, section metadata, and enrollment status

### Database
Uses MongoDB

## 4. Data Source Strategy

Bulletins API:
- Course-level data

Albert/Public Search:
- Section-level data

## 5. Data Model

Course:
```json
{
  "course_code": "CSCI-UA-101",
  "title": "...",
  "description": "...",
  "credits": 4
}
```

Section:
```json
{
  "course_code": "CSCI-UA-101",
  "section": "001",
  "meeting_times": "...",
  "status": "Open"
}
```

User:
```json
{
  "user_id": "...",
  "taken_courses": [],
  "major": "..."
}
```

## 6. AI Responsibilities

- Understand user intent
- Query database
- Generate grounded recommendations
- Avoid hallucination

## 7. Constraints

- Data may be incomplete
- External APIs may change
- Not all majors supported
- Professor-specific data is out of scope for the current version

## 8. Non-Goals

- Perfect transcript parsing
- Real-time registration integration
- Professor analytics or rating aggregation

## 9. Guidelines

- Use Docker
- Modular architecture
- Python backend
- Clear APIs

## 10. Future

- Multi-university support
- NLP transcript parsing
- GPA optimization
