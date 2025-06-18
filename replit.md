# CourtSide Club - Tennis Tournament Attendance Management Platform

## Overview

CourtSide Club is a comprehensive web application for managing tennis tournament attendance, built with Flask and PostgreSQL. The platform enables users to discover, register for, and coordinate attendance at tennis tournaments worldwide, with features for session selection, fan meetups, and lanyard merchandise fulfillment.

## System Architecture

### Backend Architecture
- **Framework**: Flask with Blueprint-based modular architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: Flask-Login with Google OAuth integration
- **Email Services**: SendGrid API for transactional emails
- **Session Management**: Server-side sessions with secure cookie configuration
- **Rate Limiting**: Flask-Limiter for API protection

### Frontend Architecture
- **Templates**: Jinja2 templating with modular component structure
- **Static Assets**: CSS, JavaScript, and image files served directly
- **Responsive Design**: Mobile-first responsive web interface
- **Form Handling**: Flask-WTF with CSRF protection

### Database Design
- **User Management**: Users table with OAuth and local authentication support
- **Tournament Data**: Tournaments table with comprehensive event information
- **Attendance Tracking**: UserTournament junction table for session-specific attendance
- **Past Tournaments**: UserPastTournament for historical attendance tracking
- **Wishlist**: UserWishlistTournament for bucket list functionality
- **Shipping**: ShippingAddress table for lanyard fulfillment

## Key Components

### User Management System
- **Authentication**: Dual authentication with Google OAuth and local accounts
- **Profile Management**: User profiles with location, preferences, and tournament history
- **Admin System**: Administrative interface with user management capabilities
- **Test Users**: Automated test user generation for QA and development

### Tournament Management
- **Tournament Data**: Comprehensive tournament information including sessions, dates, locations
- **Session Selection**: Day/Night session selection with attendance tracking
- **Tournament Discovery**: Browse tournaments by date, location, and event type
- **Past Tournament Tracking**: Historical tournament attendance management

### Attendance System
- **Session-Based Attendance**: Users select specific day/night sessions
- **Attendance States**: "Attending" vs "Maybe" attendance types
- **Meetup Coordination**: "Open to meeting other fans" functionality
- **Session Counts**: Real-time attendance counts per session

### Lanyard Fulfillment System
- **Order Management**: Lanyard ordering integrated with tournament attendance
- **Shipping Integration**: Address collection and validation
- **Export System**: CSV export for fulfillment processing
- **Order Tracking**: Status tracking from order to delivery

## Data Flow

### User Registration & Authentication Flow
1. **Registration**: Google OAuth or email/password registration
2. **Profile Setup**: Location and preference collection
3. **Tournament Discovery**: Browse available tournaments
4. **Session Selection**: Select specific day/night sessions
5. **Lanyard Ordering**: Optional lanyard merchandise ordering

### Tournament Attendance Flow
1. **Tournament Search**: Filter tournaments by criteria
2. **Tournament Details**: View sessions and attendance counts
3. **Session Selection**: Choose specific sessions to attend
4. **Meetup Preferences**: Opt-in to meeting other fans
5. **Confirmation**: Attendance confirmation and notifications

### Administrative Flow
1. **Tournament Management**: Add/edit tournament information
2. **User Management**: View and manage user accounts
3. **Attendance Monitoring**: Track attendance across tournaments
4. **Lanyard Fulfillment**: Export orders and track shipments
5. **Analytics**: View system usage and engagement metrics

## External Dependencies

### Authentication Services
- **Google OAuth**: Primary authentication provider
- **Flask-Login**: Session management and user state

### Communication Services
- **SendGrid**: Transactional email delivery
- **Email Templates**: JSON-based email template system

### Data Services
- **PostgreSQL**: Primary database with connection pooling
- **SQLAlchemy**: ORM with migration support
- **Alembic**: Database migration management

### Development & Deployment
- **Gunicorn**: Production WSGI server
- **Replit**: Development and hosting platform
- **Environment Variables**: Configuration management

## Deployment Strategy

### Environment Configuration
- **Development**: Local development with SQLite fallback
- **Production**: Replit deployment with PostgreSQL
- **Environment Variables**: Secure credential management
- **SSL/HTTPS**: Enforced secure connections

### Database Management
- **Migrations**: Python scripts for schema updates
- **Connection Pooling**: Optimized database connections
- **Backup Strategy**: Automated database backups
- **Test Data**: Automated test user generation

### Scaling Considerations
- **Connection Limits**: Database connection optimization
- **Rate Limiting**: API protection and abuse prevention
- **Caching Strategy**: Static asset and data caching
- **Error Handling**: Comprehensive error logging and recovery

## Recent Changes

### June 18, 2025 - Tournament Detail Page Enhancement
- Fixed route conflict between public and user tournament detail pages
- Reordered blueprint registration to prioritize authenticated user routes
- Successfully resolved `tournament_days length: 0` issue
- Tournament detail page now properly generates 14 days for tournaments
- **Session Visibility Logic**: Sessions now only show when user selects "Attending" or "Maybe Attending"
- **Admin Debug Control**: Debug information only visible to admin users
- **Default Checkbox Behavior**: "Open to meeting other fans" defaults to checked for attending users
- **Official Website Integration**: Added official tournament website links under tournament names
- **Enhanced User Experience**: Restored "Other tournaments fans have attended" section
- **Database State Management**: Proper handling of attendance states (attending=True/False, session_label variations)
- **CSS Improvements**: Added styling for session-hidden-message and tournament-official-link elements

## Changelog
- June 13, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.