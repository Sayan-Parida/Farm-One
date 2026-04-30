#!/usr/bin/env python3
"""Generate PDF report of FarmOne codebase analysis"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime

# Document setup
pdf_filename = "FarmOne_Codebase_Analysis_Report.pdf"
doc = SimpleDocTemplate(pdf_filename, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
story = []
styles = getSampleStyleSheet()

# Custom styles
title_style = ParagraphStyle(
    'CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    textColor=colors.HexColor('#059669'),
    spaceAfter=12,
    alignment=TA_CENTER,
    fontName='Helvetica-Bold'
)

heading_style = ParagraphStyle(
    'CustomHeading',
    parent=styles['Heading2'],
    fontSize=14,
    textColor=colors.HexColor('#047857'),
    spaceAfter=8,
    spaceBefore=8,
    fontName='Helvetica-Bold'
)

normal_style = ParagraphStyle(
    'CustomNormal',
    parent=styles['Normal'],
    fontSize=10,
    alignment=TA_JUSTIFY,
    spaceAfter=6
)

# Title
story.append(Paragraph("FARMONE: COMPREHENSIVE CODEBASE ANALYSIS REPORT", title_style))
story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
story.append(Spacer(1, 0.3*inch))

# Project Overview
story.append(Paragraph("PROJECT OVERVIEW", heading_style))
overview_text = """
<b>FarmOne</b> is an AI-powered precision agriculture platform that leverages machine learning, real-time weather data, soil analysis, and satellite imagery to provide farmers with actionable crop recommendations, yield predictions, and personalized farming advice. The application combines modern web technologies with advanced agricultural analytics to democratize access to smart farming insights.
"""
story.append(Paragraph(overview_text, normal_style))
story.append(Spacer(1, 0.15*inch))

# Tech Stack - Frontend
story.append(Paragraph("TECH STACK", heading_style))
story.append(Paragraph("<b>Frontend</b>", styles['Heading3']))
frontend_data = [
    ['Component', 'Technology', 'Version'],
    ['Framework', 'Next.js', '16.0.10'],
    ['Runtime', 'React', '19.2.0'],
    ['Language', 'TypeScript', '5'],
    ['Styling', 'TailwindCSS + PostCSS', '4.1.9'],
    ['UI Components', 'Radix UI', 'Multiple'],
    ['Form Validation', 'React Hook Form + Zod', '7.60.0 / 3.25.76'],
    ['Charts', 'Recharts', '2.15.4'],
    ['Maps', 'Leaflet', '1.9.4'],
    ['Notifications', 'Sonner', '1.7.4'],
    ['Theming', 'Next-Themes', '0.4.6'],
]
frontend_table = Table(frontend_data)
frontend_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
]))
story.append(frontend_table)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("<b>Backend</b>", styles['Heading3']))
backend_data = [
    ['Component', 'Technology', 'Version'],
    ['Framework', 'FastAPI', '0.109.0'],
    ['Server', 'Uvicorn', '0.27.0'],
    ['Validation', 'Pydantic', '2.5.3'],
    ['HTTP Client', 'HTTPX', '0.26.0'],
    ['Environment', 'Python-DotEnv', '1.0.0'],
    ['Python', '3.x with venv', 'Latest'],
]
backend_table = Table(backend_data)
backend_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
]))
story.append(backend_table)
story.append(Spacer(1, 0.15*inch))

story.append(Paragraph("<b>Machine Learning & AI</b>", styles['Heading3']))
ml_data = [
    ['Component', 'Technology', 'Details'],
    ['ML Libraries', 'scikit-learn', 'Random Forest models'],
    ['Data Processing', 'Pandas, NumPy', 'Feature engineering'],
    ['Model Storage', 'Joblib', 'Model serialization'],
    ['Crop Prediction', 'Random Forest Classifier', '200 estimators'],
    ['Yield Prediction', 'Random Forest Regressor', '300 estimators'],
    ['Advisory LLM', 'Mistral 7B', 'Via OpenRouter'],
    ['Chatbot LLM', 'Llama 3.1 8B', 'Via OpenRouter'],
]
ml_table = Table(ml_data)
ml_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
]))
story.append(ml_table)
story.append(Spacer(1, 0.2*inch))

# Page Break
story.append(PageBreak())

# Core Features
story.append(Paragraph("CORE FEATURES & FUNCTIONALITY", heading_style))

features_text = """
<b>1. Crop Recommendation System</b><br/>
Input: Temperature, humidity, rainfall, soil pH | Model: Random Forest Classifier (200 estimators) | 
Output: Top 3 recommended crops with success probability<br/><br/>

<b>2. Yield Prediction Engine</b><br/>
Input: Min/max temperature, 7-day rainfall, humidity, soil pH, organic carbon | 
Model: Random Forest Regressor (300 estimators) | Output: Expected yield (tons/hectare)<br/><br/>

<b>3. Real-Time Weather Integration</b><br/>
Fetches current conditions from OpenWeather API | Extracts: temperature, humidity, rainfall, description |
Async operations for performance<br/><br/>

<b>4. Soil Analysis Service</b><br/>
Queries SoilGrids API for scientific soil data (0-5cm depth) | Properties: pH, organic carbon, texture |
USDA soil classification<br/><br/>

<b>5. FarmBot AI Assistant</b><br/>
Dual LLM Architecture: Advisory LLM (Mistral 7B) + Chat LLM (Llama 3.1 8B) | 
Strict agriculture-only context | Integrated with all data sources<br/><br/>

<b>6. Interactive Map Interface</b><br/>
Leaflet-based geospatial visualization | Click-to-analyze functionality | Real-time marker placement
"""
story.append(Paragraph(features_text, normal_style))
story.append(Spacer(1, 0.2*inch))

# Project Capabilities
story.append(Paragraph("PROJECT SCOPE & CAPABILITIES", heading_style))

capabilities_data = [
    ['Capability', 'Status'],
    ['Geospatial Analysis', '✅'],
    ['Data Aggregation (Weather + Soil)', '✅'],
    ['ML Predictions (Crops & Yield)', '✅'],
    ['AI-Powered Advisory', '✅'],
    ['Conversational Chatbot', '✅'],
    ['Multi-page Dashboard', '✅'],
    ['Real-time Updates', '✅'],
    ['Responsive Design', '✅'],
    ['Satellite Imagery Processing', '❌'],
    ['Historical Trends', '❌'],
    ['User Authentication', '❌'],
    ['Database Integration', '❌'],
]

cap_table = Table(capabilities_data)
cap_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
]))
story.append(cap_table)
story.append(Spacer(1, 0.2*inch))

# API Endpoints
story.append(Paragraph("API ENDPOINTS", heading_style))

api_data = [
    ['Endpoint', 'Method', 'Purpose'],
    ['/', 'GET', 'Health check'],
    ['/api/analyze?lat={lat}&lon={lon}', 'GET', 'Weather + soil analysis'],
    ['/api/ml/crop', 'POST', 'Crop recommendation'],
    ['/api/ml/yield', 'POST', 'Yield prediction'],
    ['/api/ml/advisory', 'POST', 'Farming advice'],
    ['/api/chat', 'POST', 'Chatbot questions'],
    ['/docs', 'GET', 'Swagger UI'],
    ['/redoc', 'GET', 'ReDoc documentation'],
]

api_table = Table(api_data)
api_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 8),
]))
story.append(api_table)
story.append(Spacer(1, 0.2*inch))

# Page Break
story.append(PageBreak())

# Deployment & Environment
story.append(Paragraph("DEPLOYMENT & ENVIRONMENT", heading_style))

deploy_text = """
<b>Frontend Deployment (Vercel)</b><br/>
Build: <font face="Courier">npm run build</font> | Start: <font face="Courier">npm start</font> | 
Dev: <font face="Courier">npm run dev</font><br/><br/>

<b>Backend Deployment</b><br/>
Development: <font face="Courier">python -m uvicorn main:app --reload</font><br/>
Production: <font face="Courier">python -m uvicorn main:app --host 0.0.0.0 --port 8000</font><br/>
Documentation: Swagger UI at <font face="Courier">/docs</font>, ReDoc at <font face="Courier">/redoc</font><br/><br/>

<b>Required Environment Variables</b><br/>
• OPENWEATHER_API_KEY<br/>
• OPENROUTER_API_KEY (fallback)<br/>
• OPENROUTER_ADVISORY_API_KEY<br/>
• OPENROUTER_CHATBOT_API_KEY<br/>
• NEXT_PUBLIC_API_BASE
"""
story.append(Paragraph(deploy_text, normal_style))
story.append(Spacer(1, 0.2*inch))

# External APIs
story.append(Paragraph("EXTERNAL DATA SOURCES", heading_style))
external_data = [
    ['Source', 'Provider', 'Purpose', 'Cost'],
    ['Weather', 'OpenWeather API', 'Real-time conditions', 'Free tier available'],
    ['Soil Data', 'SoilGrids API', 'Soil properties (0-5cm)', 'Free, no auth'],
    ['LLM Services', 'OpenRouter', 'Advisory & Chat', 'Pay-per-token'],
    ['Deployment', 'Vercel', 'Frontend hosting', 'Free tier available'],
]

ext_table = Table(external_data)
ext_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ('FONTSIZE', (0, 1), (-1, -1), 9),
]))
story.append(ext_table)
story.append(Spacer(1, 0.2*inch))

# Architecture Overview
story.append(Paragraph("SYSTEM ARCHITECTURE", heading_style))

arch_text = """
FarmOne follows a three-tier client-server architecture:<br/><br/>

<b>Tier 1: Frontend (Next.js/React)</b> - Responsive UI with geospatial interface<br/>
<b>Tier 2: API Layer (Next.js Routes)</b> - Proxy requests to backend<br/>
<b>Tier 3: Backend (FastAPI/Python)</b> - Business logic, ML models, LLM integration<br/>
<b>Tier 4: External Services</b> - Weather API, Soil Database, LLM Provider<br/><br/>

<b>Data Flow:</b><br/>
1. User selects location on interactive map<br/>
2. Frontend sends request to Next.js API route<br/>
3. Backend fetches weather (OpenWeather) and soil (SoilGrids) data<br/>
4. ML models process data (crop recommendation, yield prediction)<br/>
5. LLMs generate contextual advice and responses<br/>
6. Results displayed with visualizations in frontend<br/>
"""
story.append(Paragraph(arch_text, normal_style))
story.append(Spacer(1, 0.2*inch))

# Page Break
story.append(PageBreak())

# Security & Scalability
story.append(Paragraph("SECURITY & SCALABILITY", heading_style))

security_text = """
<b>Current Security Considerations:</b><br/>
⚠️ API keys in .env (standard practice, needs protection in production)<br/>
⚠️ CORS set to "*" (allows any origin)<br/>
⚠️ No rate limiting on endpoints<br/>
⚠️ No input validation for coordinates<br/>
⚠️ LLM guardrails rely on prompt engineering<br/><br/>

<b>Scalability Features:</b><br/>
✅ Stateless backend (horizontally scalable)<br/>
✅ Async/await operations (concurrent requests)<br/>
✅ No database required for MVP<br/>
❌ No caching (every request queries APIs)<br/>
❌ No authentication system<br/><br/>

<b>Recommended Improvements:</b><br/>
• Redis caching for weather/soil data (24hr TTL)<br/>
• JWT authentication for user management<br/>
• PostgreSQL for historical data storage<br/>
• Rate limiting with API keys<br/>
• Input validation and sanitization<br/>
• Background job scheduling (forecasts, analytics)<br/>
• WebSocket support for real-time collaboration<br/>
"""
story.append(Paragraph(security_text, normal_style))
story.append(Spacer(1, 0.2*inch))

# Project Maturity
story.append(Paragraph("PROJECT MATURITY ASSESSMENT", heading_style))

maturity_text = """
<b>Development Stage:</b> MVP / Beta<br/><br/>

<b>Strengths:</b><br/>
• Core functionality complete and working<br/>
• ML models trained and integrated<br/>
• Frontend responsive and professionally styled<br/>
• Backend architecturally sound with async operations<br/>
• Clear separation of concerns<br/>
• Modern tech stack with good developer experience<br/><br/>

<b>Missing Elements (Production):</b><br/>
• Rate limiting and throttling<br/>
• User authentication and authorization<br/>
• Data persistence and historical analysis<br/>
• Monitoring and logging infrastructure<br/>
• Error recovery and fallback mechanisms<br/>
• Load testing and performance optimization<br/>
• Comprehensive test coverage<br/><br/>

<b>Estimated Lines of Code:</b> ~2,000+ (excluding node_modules and UI library)<br/>
<b>Code Quality:</b> Good architectural patterns, modular design<br/>
<b>Documentation:</b> Present (README files, inline comments)<br/>
"""
story.append(Paragraph(maturity_text, normal_style))
story.append(Spacer(1, 0.2*inch))

# Summary
story.append(Paragraph("SUMMARY", heading_style))

summary_text = """
<b>FarmOne</b> is a sophisticated precision agriculture platform that successfully bridges the gap between raw 
agricultural data and actionable farmer insights through intelligent processing and conversational AI. The application 
demonstrates solid software engineering practices with a modern tech stack, clear architecture, and practical farm value.<br/><br/>

<b>Key Differentiators:</b><br/>
• Real-time integration with scientific soil and weather databases<br/>
• Multiple ML models for crop and yield prediction<br/>
• Dual LLM setup for contextual advice and general Q&A<br/>
• Interactive geospatial interface for location-based analysis<br/>
• Responsive, production-quality frontend design<br/><br/>

The platform is ready for MVP deployment and early-stage farming operations. Production hardening, scaling infrastructure, 
and user management features would be the next priorities for enterprise deployment.<br/><br/>

<b>Ideal For:</b> Agricultural research, farming decision support, educational institutions, agritech startups seeking 
rapid prototyping of ML-powered farming solutions.
"""
story.append(Paragraph(summary_text, normal_style))

# Build PDF
doc.build(story)
print(f"✅ PDF Report Generated: {pdf_filename}")
print(f"📄 Location: {pdf_filename}")
print(f"📊 Size: Professional multi-page formatted report")
