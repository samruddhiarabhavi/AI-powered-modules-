Rayeva AI Systems – Sustainable Commerce AI Platform

AI-powered platform for sustainable commerce automation built as part of the Rayeva AI Systems Assessment.

This system provides intelligent automation for e-commerce and B2B platforms through four AI modules:

Product Category Tagging

B2B Proposal Generation

Sustainability Impact Reporting

WhatsApp AI Assistant

The API is built using FastAPI with OpenAPI 3.1 documentation.

Project Architecture
Rayeva AI Platform
│
├── Module 1: Category Tagger
├── Module 2: B2B Proposal Generator
├── Module 3: Impact Reporter
├── Module 4: WhatsApp Bot
│
└── REST API (FastAPI)
Tech Stack

Python

FastAPI

OpenAPI 3.1 / Swagger UI

AI Prompt Processing

REST API Architecture

JSON Data Processing

API Documentation

Swagger API documentation is automatically generated.

After running the server open:

http://localhost:8000/docs

OpenAPI Schema:

http://localhost:8000/openapi.json
Module 1: Category Tagger

AI system that automatically categorizes products based on their name and description.

Endpoints

Categorize a product

POST /api/category-tagger/categorize

Example request:

{
  "name": "Organic Cotton T-Shirt",
  "description": "Eco friendly cotton shirt",
  "product_id": 101
}

Batch categorization

POST /api/category-tagger/categorize/batch

Get available categories

GET /api/category-tagger/categories
Module 2: B2B Proposal Generator

Automatically generates procurement proposals for B2B clients using AI.

Endpoint
POST /api/b2b-proposal/generate

Example:

{
  "client_id": 10,
  "budget": 5000,
  "requirements": {
    "product": "Eco packaging",
    "quantity": 1000
  }
}

Retrieve proposal:

GET /api/b2b-proposal/proposals/{proposal_id}
Module 3: Impact Reporter

Generates sustainability reports for completed orders, including environmental impact metrics.

Endpoint

Generate report:

POST /api/impact-reporter/generate/{order_id}

Retrieve report:

GET /api/impact-reporter/reports/{report_id}
Module 4: WhatsApp AI Bot

WhatsApp chatbot that allows users to interact with the platform.

Supports:

Customer queries

Product support

Automation workflows

Endpoints

Webhook endpoint

POST /api/whatsapp-bot/webhook

Test bot

POST /api/whatsapp-bot/test

Get bot statistics

GET /api/whatsapp-bot/stats
Health Check
GET /health

Returns system status.

Running the Project
1 Install dependencies
pip install -r requirements.txt
2 Run the server
uvicorn main:app --reload
3 Open API docs
http://localhost:8000/docs
Example Project Output

The API returns structured JSON responses such as:

{
  "success": true,
  "data": {
    "category": "Sustainable Clothing"
  },
  "duration_ms": 210
}
Project Purpose

This project demonstrates:

AI-driven automation

REST API design

scalable microservice modules

sustainable commerce workflows

AI integration with business processes

Author

Developed by:

Samruddhi Arabhavi
Computer Science Engineering Student
AI & Full-Stack Developer
