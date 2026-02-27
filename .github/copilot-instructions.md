# Exertia Backend - Copilot Instructions

## Project Overview
- **Type**: Django REST API Backend
- **Language**: Python 3.12+
- **Framework**: Django 5.x with Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)

## Project Structure
- `config/` - Django project settings and configuration
- `core/` - Core application with shared models and utilities
- `manage.py` - Django management script

## Development Guidelines
- Use environment variables for sensitive settings (via python-decouple)
- Follow Django best practices for app structure
- Use Django REST Framework for API endpoints
- Write views as class-based views where possible
- Keep business logic in models or service layers, not in views
