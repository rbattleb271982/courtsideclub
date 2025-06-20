# Let'CourtSide AI Agents System Summary

## System Overview
Let'CourtSide utilizes 6 AI-powered automation agents to manage user communications, content generation, and administrative operations for tennis tournament attendance management.

## Agent Inventory

| Agent Name | Description | Trigger Type | External Services | Key Data Sources | Output Type | Route/Trigger |
|------------|-------------|--------------|-------------------|------------------|-------------|---------------|
| **Email Reminder Agent** | Sends tournament reminder emails to users attending tournaments starting in 12-15 days | Manual | SendGrid | User, Tournament, UserTournament | Email | `/admin/agents/run/email_reminder` |
| **Pre-Tournament Reminder Agent** | Sends reminder emails 1-2 days before a user's earliest selected tournament session | Triggered | SendGrid | User, Tournament, UserTournament | Email | `/admin/agents/run/pre_tournament_reminder` |
| **Post-Event Follow-Up Agent** | Sends thank-you emails to users who attended tournaments that ended yesterday | Triggered | SendGrid | User, Tournament, UserTournament | Email | `/admin/agents/run/post_event_followup` |
| **Lanyard Reminder Agent** | Sends reminder emails to users with lanyard orders attending tournaments in exactly 3 days | Daily | SendGrid | User, Tournament, UserTournament | Email | `/admin/agents/run/lanyard_reminder` |
| **Tournament Summary Agent** | Generates AI-powered editorial summaries for tournaments missing descriptions | Triggered | OpenAI GPT-4 | Tournament | Content Update | `/admin/agents/run/tournament_summary` |
| **Lanyard Export Agent** | Exports unfulfilled lanyard orders to CSV for daily fulfillment processing | Daily | None | User, UserTournament, ShippingAddress | CSV Download | `/admin/agents/run/lanyard_export` |
| **Blog Generator Agent** | Suggests and generates SEO blog content for upcoming tournaments | Manual | OpenAI GPT-4 | Tournament | Content Suggestions | `/admin/agents/blog` |

## Technical Architecture

### Email Infrastructure
- **Service**: SendGrid API integration
- **Templates**: JSON-based email templates in `/config/email_templates.json`
- **Targeting**: Users with valid email addresses and specific tournament selections
- **Delivery**: Automated scheduling with manual override capabilities

### AI Content Generation
- **Service**: OpenAI GPT-4 API
- **Use Cases**: Tournament summaries, blog topic generation
- **Data Processing**: Tournament metadata analysis for context-aware content

### Data Export System
- **Format**: CSV files with customer details and shipping addresses
- **Processing**: Batch exports of unfulfilled lanyard orders
- **Tracking**: Boolean flags to prevent duplicate exports

### Agent Scheduling
- **Daily Agents**: Lanyard Reminder, Lanyard Export
- **Triggered Agents**: Pre-Tournament Reminder, Post-Event Follow-Up, Tournament Summary
- **Manual Agents**: Email Reminder, Blog Generator

## Data Flow Patterns

### User Communication Flow
1. **User Registration** → Tournament Selection → Session Selection
2. **Agent Triggers** → Email Template Loading → Personalization
3. **SendGrid Delivery** → User Engagement → Follow-up Actions

### Content Generation Flow
1. **Tournament Data** → AI Processing → Content Generation
2. **Admin Review** → Content Publication → SEO Optimization

### Administrative Operations
1. **Order Processing** → CSV Export → Fulfillment Integration
2. **Status Tracking** → Database Updates → Reporting

## Security & Compliance
- **API Keys**: Environment variable storage for SendGrid and OpenAI
- **Data Privacy**: Email targeting based on user consent and selections
- **Error Handling**: Comprehensive logging and timeout management
- **Admin Controls**: Role-based access to agent execution

## Performance Metrics
- **Email Delivery**: Targeted user segments based on tournament timing
- **Content Generation**: Automated summary creation for tournament descriptions
- **Export Efficiency**: Batch processing with 100-order limits per export
- **Execution Monitoring**: Manual triggers with admin feedback and logging

## Integration Points
- **Database**: PostgreSQL with User, Tournament, UserTournament, ShippingAddress models
- **Email Service**: SendGrid with template-based messaging
- **AI Service**: OpenAI GPT-4 for content generation
- **Admin Interface**: Flask-based control panel with manual execution capabilities

---

<div align="center">

## What's Next for Let'CourtSide

Let'CourtSide is just getting started.

In the future, we're building toward a members-club-style experience — like the ones you see at tournaments — but for fans.

Think:
• Priority access to meet-ups
• Easy tools to plan your tournament trips
• Exclusive lounge-style perks

*When enough of us join, we can make the match-day experience better together.*

</div>