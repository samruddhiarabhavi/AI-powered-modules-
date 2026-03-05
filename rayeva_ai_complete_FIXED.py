"""
RAYEVA AI SYSTEMS - COMPLETE APPLICATION WITH ALL 4 MODULES
===========================================================
AI-Powered Modules for Sustainable Commerce Automation

MODULES IMPLEMENTED:
1. AI Category Tagger - Auto-categorize products
2. B2B Proposal Generator - Generate business proposals
3. Impact Reporter - Generate sustainability impact reports
4. WhatsApp Bot - Customer support automation

SETUP:
1. Install: pip install fastapi uvicorn anthropic sqlalchemy pydantic-settings loguru python-dotenv
2. Create .env file with ANTHROPIC_API_KEY
3. Run: python rayeva_all_4_modules.py
4. Access: http://localhost:8000/docs

Author: Rayeva AI Assignment - ALL 4 MODULES
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Generator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import enum

# FastAPI imports
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Database imports
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, JSON, func, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

# AI imports
from anthropic import Anthropic

# Logging
from loguru import logger

# Twilio (optional)
try:
    from twilio.rest import Client
    from twilio.twiml.messaging_response import MessagingResponse
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_environment: str = Field(default="development", alias="API_ENVIRONMENT")
    
    # Anthropic AI Configuration
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL")
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///./rayeva.db", alias="DATABASE_URL")
    
    # Twilio WhatsApp Configuration
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_number: str = Field(default="", alias="TWILIO_WHATSAPP_NUMBER")
    verified_whatsapp_numbers: str = Field(default="", alias="VERIFIED_WHATSAPP_NUMBERS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file_path: str = Field(default="logs/rayeva.log", alias="LOG_FILE_PATH")
    
    # Business Configuration
    product_categories: str = Field(
        default="Kitchen & Dining,Personal Care,Home & Living,Office Supplies,Packaging,Gifts & Accessories,Fashion & Apparel,Baby & Kids,Pet Care,Garden & Outdoor",
        alias="PRODUCT_CATEGORIES"
    )
    sustainability_filters: str = Field(
        default="plastic-free,compostable,biodegradable,vegan,cruelty-free,organic,recycled,upcycled,fair-trade,carbon-neutral,zero-waste,renewable",
        alias="SUSTAINABILITY_FILTERS"
    )
    
    # AI Configuration
    ai_max_tokens: int = Field(default=2000, alias="AI_MAX_TOKENS")
    ai_temperature: float = Field(default=0.7, alias="AI_TEMPERATURE")
    enable_ai_logging: bool = Field(default=True, alias="ENABLE_AI_LOGGING")
    
    @property
    def product_categories_list(self) -> List[str]:
        return [cat.strip() for cat in self.product_categories.split(",")]
    
    @property
    def sustainability_filters_list(self) -> List[str]:
        return [f.strip() for f in self.sustainability_filters.split(",")]
    
    @property
    def verified_numbers_list(self) -> List[str]:
        if not self.verified_whatsapp_numbers:
            return []
        return [num.strip() for num in self.verified_whatsapp_numbers.split(",")]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# ============================================================================
# DATABASE SETUP
# ============================================================================

settings = get_settings()

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.api_environment == "development"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency function to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# DATABASE MODELS
# ============================================================================

class AILog(Base):
    """AI interaction log table."""
    __tablename__ = "ai_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    module_name = Column(String(100), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text, nullable=True)
    ai_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class Product(Base):
    """Product table with AI-generated categorization."""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    sku = Column(String(100), unique=True, index=True, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # AI-Generated Categorization
    primary_category = Column(String(100), nullable=True, index=True)
    sub_category = Column(String(100), nullable=True, index=True)
    seo_tags = Column(JSON, nullable=True)
    sustainability_filters = Column(JSON, nullable=True)
    
    # AI Metadata
    ai_categorization_data = Column(JSON, nullable=True)
    ai_confidence_score = Column(Float, nullable=True)
    
    # Impact Metrics (for Module 3)
    conventional_plastic_g = Column(Float, default=0)
    product_plastic_g = Column(Float, default=0)
    carbon_footprint_kg = Column(Float, default=0)
    water_usage_liters = Column(Float, default=0)
    local_sourced = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_ai_categorized = Column(Boolean, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    categorized_at = Column(DateTime(timezone=True), nullable=True)


class Order(Base):
    """Order table for tracking customer purchases."""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # Customer Info
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=True, index=True)
    customer_phone = Column(String(20), nullable=True, index=True)
    
    # Order Details
    total_amount = Column(Float, nullable=False)
    items = Column(JSON, nullable=False)
    shipping_address = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default="pending", index=True)
    payment_status = Column(String(50), default="pending")
    
    # Tracking
    tracking_number = Column(String(100), nullable=True)
    estimated_delivery = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    shipped_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)


class WhatsAppConversation(Base):
    """WhatsApp conversation log table."""
    __tablename__ = "whatsapp_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # WhatsApp Info
    from_number = Column(String(50), nullable=False, index=True)
    to_number = Column(String(50), nullable=False)
    message_sid = Column(String(100), unique=True, nullable=True)
    
    # Message Content
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=True)
    intent = Column(String(100), nullable=True, index=True)
    
    # AI Metadata
    ai_response_data = Column(JSON, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    
    # Escalation
    escalated = Column(Boolean, default=False, index=True)
    escalation_reason = Column(Text, nullable=True)
    
    # Context
    order_number = Column(String(50), nullable=True, index=True)
    related_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)


class B2BClient(Base):
    """B2B client table for proposal generation."""
    __tablename__ = "b2b_clients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class B2BProposal(Base):
    """B2B proposal table."""
    __tablename__ = "b2b_proposals"
    
    id = Column(Integer, primary_key=True, index=True)
    proposal_number = Column(String(50), unique=True, nullable=False, index=True)
    client_id = Column(Integer, nullable=False, index=True)
    
    # Requirements
    budget = Column(Float, nullable=False)
    requirements = Column(JSON, nullable=False)
    
    # AI-Generated Proposal
    selected_products = Column(JSON, nullable=False)
    total_cost = Column(Float, nullable=False)
    sustainability_score = Column(Float, nullable=True)
    ai_justification = Column(Text, nullable=True)
    
    # Alternative Proposals
    alternatives = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(50), default="draft", index=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ImpactReport(Base):
    """Impact report table."""
    __tablename__ = "impact_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_number = Column(String(50), unique=True, nullable=False, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    
    # Impact Metrics
    plastic_saved_kg = Column(Float, default=0)
    carbon_avoided_kg = Column(Float, default=0)
    water_saved_liters = Column(Float, default=0)
    local_sourcing_percentage = Column(Float, default=0)
    
    # AI-Generated Narrative
    impact_narrative = Column(Text, nullable=True)
    comparisons = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ============================================================================
# AI CLIENT
# ============================================================================

class AIClient:
    """Centralized AI client for Anthropic Claude API interactions."""
    
    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.max_tokens = settings.ai_max_tokens
        self.temperature = settings.ai_temperature
    
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        module_name: str = "general",
        request_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate AI completion with automatic logging."""
        start_time = datetime.utcnow()
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt or "",
                messages=messages
            )
            
            response_text = response.content[0].text
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            result = {
                "success": True,
                "response": response_text,
                "model": self.model,
                "tokens_used": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                    "total": response.usage.input_tokens + response.usage.output_tokens
                },
                "duration_ms": duration_ms,
                "request_metadata": request_metadata or {}
            }
            
            if settings.enable_ai_logging:
                self._log_interaction(
                    module_name=module_name,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response=response_text,
                    tokens_used=result["tokens_used"]["total"],
                    duration_ms=duration_ms,
                    success=True,
                    ai_metadata=request_metadata
                )
            
            return result
            
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            logger.error(f"AI generation failed: {str(e)}")
            
            if settings.enable_ai_logging:
                self._log_interaction(
                    module_name=module_name,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response=None,
                    tokens_used=0,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(e),
                    ai_metadata=request_metadata
                )
            
            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms
            }
    
    async def generate_structured_json(
        self,
        prompt: str,
        system_prompt: str,
        expected_schema: Dict[str, Any],
        module_name: str = "general",
        request_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output from AI."""
        enhanced_system = f"""{system_prompt}

CRITICAL: You must respond ONLY with valid JSON. Do not include any explanatory text before or after the JSON.
Do not use markdown code blocks. Return raw JSON only.

Expected schema structure:
{json.dumps(expected_schema, indent=2)}
"""
        
        result = await self.generate_completion(
            prompt=prompt,
            system_prompt=enhanced_system,
            temperature=0.3,
            module_name=module_name,
            request_metadata=request_metadata
        )
        
        if not result["success"]:
            return result
        
        try:
            response_text = result["response"].strip()
            
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            parsed_json = json.loads(response_text)
            result["parsed_data"] = parsed_json
            result["raw_response"] = result["response"]
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {
                "success": False,
                "error": f"Invalid JSON response: {str(e)}",
                "raw_response": result["response"]
            }
    
    def _log_interaction(
        self,
        module_name: str,
        prompt: str,
        system_prompt: Optional[str],
        response: Optional[str],
        tokens_used: int,
        duration_ms: int,
        success: bool,
        error_message: Optional[str] = None,
        ai_metadata: Optional[Dict[str, Any]] = None
    ):
        """Log AI interaction to database."""
        try:
            with get_db_context() as db:
                log_entry = AILog(
                    module_name=module_name,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response=response,
                    tokens_used=tokens_used,
                    duration_ms=duration_ms,
                    success=success,
                    error_message=error_message,
                    ai_metadata=ai_metadata or {}
                )
                db.add(log_entry)
        except Exception as e:
            logger.error(f"Failed to log AI interaction: {str(e)}")


# Singleton instance
ai_client = AIClient()


# ============================================================================
# MODULE 1: CATEGORY TAGGER SERVICE
# ============================================================================

class CategoryTaggerService:
    """Service for AI-powered product categorization and tagging."""
    
    def __init__(self):
        self.categories = settings.product_categories_list
        self.sustainability_filters = settings.sustainability_filters_list
    
    async def categorize_product(
        self,
        product_name: str,
        product_description: Optional[str] = None,
        product_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Categorize a product using AI."""
        prompt = self._build_categorization_prompt(product_name, product_description)
        system_prompt = self._build_system_prompt()
        
        expected_schema = {
            "primary_category": "string",
            "sub_category": "string",
            "seo_tags": ["string"],
            "sustainability_filters": ["string"],
            "confidence_score": "number (0-100)",
            "reasoning": "string"
        }
        
        result = await ai_client.generate_structured_json(
            prompt=prompt,
            system_prompt=system_prompt,
            expected_schema=expected_schema,
            module_name="category_tagger",
            request_metadata={"product_name": product_name, "product_id": product_id}
        )
        
        if not result["success"]:
            logger.error(f"Failed to categorize product: {result.get('error')}")
            return result
        
        categorization = result["parsed_data"]
        validated_data = self._validate_categorization(categorization)
        
        if product_id:
            self._update_product_categorization(product_id, validated_data)
        
        return {
            "success": True,
            "data": validated_data,
            "tokens_used": result["tokens_used"],
            "duration_ms": result["duration_ms"]
        }
    
    async def batch_categorize(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize multiple products in batch."""
        results = []
        for product in products:
            result = await self.categorize_product(
                product_name=product.get("name"),
                product_description=product.get("description"),
                product_id=product.get("id")
            )
            results.append({
                "product_id": product.get("id"),
                "product_name": product.get("name"),
                **result
            })
        return results
    
    def _build_categorization_prompt(self, product_name: str, product_description: Optional[str]) -> str:
        """Build the categorization prompt."""
        prompt = f"""Product Name: {product_name}"""
        if product_description:
            prompt += f"\n\nProduct Description: {product_description}"
        
        prompt += """

Please analyze this sustainable commerce product and provide:
1. The most appropriate primary category from the available list
2. A specific sub-category that fits the product
3. 5-10 SEO tags that would help customers find this product
4. Applicable sustainability filters based on the product characteristics
5. A confidence score (0-100) for your categorization
6. Brief reasoning for your choices
"""
        return prompt
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with business rules."""
        return f"""You are an expert product categorization AI for Rayeva, a sustainable commerce platform.

AVAILABLE PRIMARY CATEGORIES:
{', '.join(self.categories)}

AVAILABLE SUSTAINABILITY FILTERS:
{', '.join(self.sustainability_filters)}

RULES:
1. primary_category MUST be one of the available categories listed above
2. sub_category should be specific and descriptive (e.g., "Reusable Water Bottles", "Bamboo Cutlery")
3. Generate 5-10 relevant SEO tags (lowercase, hyphen-separated)
4. Only include sustainability_filters that genuinely apply to the product
5. confidence_score should reflect how well the product fits the chosen category (0-100)
6. reasoning should be 1-2 sentences explaining your categorization logic

RESPONSE FORMAT:
Return ONLY valid JSON with this exact structure:
{{
  "primary_category": "Kitchen & Dining",
  "sub_category": "Reusable Straws",
  "seo_tags": ["eco-friendly", "reusable", "zero-waste", "sustainable", "stainless-steel"],
  "sustainability_filters": ["plastic-free", "zero-waste"],
  "confidence_score": 95,
  "reasoning": "This product clearly fits Kitchen & Dining as it's a dining accessory, with strong sustainability credentials."
}}
"""
    
    def _validate_categorization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean categorization data."""
        if data.get("primary_category") not in self.categories:
            logger.warning(f"Invalid category: {data.get('primary_category')}, using first category")
            data["primary_category"] = self.categories[0]
        
        valid_filters = [
            f for f in data.get("sustainability_filters", [])
            if f in self.sustainability_filters
        ]
        data["sustainability_filters"] = valid_filters
        
        data["seo_tags"] = [tag.lower().strip() for tag in data.get("seo_tags", [])][:10]
        
        confidence = data.get("confidence_score", 50)
        data["confidence_score"] = max(0, min(100, confidence))
        
        return data
    
    def _update_product_categorization(self, product_id: int, categorization: Dict[str, Any]):
        """Update product in database with categorization data."""
        try:
            with get_db_context() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                
                if product:
                    product.primary_category = categorization["primary_category"]
                    product.sub_category = categorization["sub_category"]
                    product.seo_tags = categorization["seo_tags"]
                    product.sustainability_filters = categorization["sustainability_filters"]
                    product.ai_confidence_score = categorization["confidence_score"]
                    product.ai_categorization_data = categorization
                    product.is_ai_categorized = True
                    product.categorized_at = datetime.utcnow()
                    
                    logger.info(f"Updated product {product_id} with AI categorization")
                else:
                    logger.warning(f"Product {product_id} not found for update")
        except Exception as e:
            logger.error(f"Failed to update product categorization: {str(e)}")


category_tagger_service = CategoryTaggerService()


# ============================================================================
# MODULE 2: B2B PROPOSAL GENERATOR SERVICE
# ============================================================================

class B2BProposalService:
    """Service for AI-powered B2B proposal generation."""
    
    async def generate_proposal(
        self,
        client_id: int,
        budget: float,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate B2B proposal using AI."""
        # Get available products
        products = self._get_available_products()
        
        # Build AI prompt
        prompt = self._build_proposal_prompt(budget, requirements, products)
        system_prompt = self._build_system_prompt()
        
        expected_schema = {
            "selected_products": [
                {
                    "product_id": "number",
                    "name": "string",
                    "quantity": "number",
                    "unit_price": "number",
                    "total_price": "number",
                    "justification": "string"
                }
            ],
            "total_cost": "number",
            "budget_utilization_percentage": "number",
            "sustainability_score": "number (0-100)",
            "overall_justification": "string",
            "alternatives": ["string"]
        }
        
        result = await ai_client.generate_structured_json(
            prompt=prompt,
            system_prompt=system_prompt,
            expected_schema=expected_schema,
            module_name="b2b_proposal",
            request_metadata={"client_id": client_id, "budget": budget}
        )
        
        if not result["success"]:
            return result
        
        proposal_data = result["parsed_data"]
        
        # Save to database
        proposal_id = self._save_proposal(client_id, budget, requirements, proposal_data)
        
        return {
            "success": True,
            "proposal_id": proposal_id,
            "data": proposal_data,
            "tokens_used": result["tokens_used"],
            "duration_ms": result["duration_ms"]
        }
    
    def _build_proposal_prompt(
        self,
        budget: float,
        requirements: Dict[str, Any],
        products: List[Dict[str, Any]]
    ) -> str:
        """Build the proposal generation prompt."""
        return f"""Generate a B2B procurement proposal for sustainable products.

BUDGET: ₹{budget:,.2f}

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

AVAILABLE PRODUCTS:
{json.dumps(products, indent=2)}

INSTRUCTIONS:
1. Select the optimal mix of products that meet the requirements
2. Stay within budget (utilize 95-100% of budget)
3. Maximize sustainability impact
4. Include 3-5 different product categories
5. Provide justification for each product selection
6. Suggest alternatives if applicable
"""
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for proposal generation."""
        return """You are an expert procurement consultant specializing in sustainable business supplies.

GUIDELINES:
1. Budget Optimization: Utilize 95-100% of available budget
2. Product Mix: Select 3-5 different product categories for variety
3. Sustainability Priority: Maximize eco-friendly impact
4. Practical Quantities: Consider minimum order quantities and practical usage
5. Clear Justification: Explain why each product was selected

RESPONSE FORMAT: Return ONLY valid JSON with selected products, costs, and justifications."""
    
    def _get_available_products(self) -> List[Dict[str, Any]]:
        """Get available products from database."""
        try:
            with get_db_context() as db:
                products = db.query(Product).filter(Product.is_active == True).all()
                
                return [
                    {
                        "id": p.id,
                        "name": p.name,
                        "description": p.description,
                        "price": p.price,
                        "category": p.primary_category,
                        "sustainability_filters": p.sustainability_filters or []
                    }
                    for p in products
                ]
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return []
    
    def _save_proposal(
        self,
        client_id: int,
        budget: float,
        requirements: Dict[str, Any],
        proposal_data: Dict[str, Any]
    ) -> int:
        """Save proposal to database."""
        try:
            with get_db_context() as db:
                # Generate proposal number
                proposal_number = f"PROP-{datetime.now().strftime('%Y%m%d')}-{client_id:04d}"
                
                proposal = B2BProposal(
                    proposal_number=proposal_number,
                    client_id=client_id,
                    budget=budget,
                    requirements=requirements,
                    selected_products=proposal_data.get("selected_products", []),
                    total_cost=proposal_data.get("total_cost", 0),
                    sustainability_score=proposal_data.get("sustainability_score", 0),
                    ai_justification=proposal_data.get("overall_justification", ""),
                    alternatives=proposal_data.get("alternatives", []),
                    status="draft"
                )
                db.add(proposal)
                db.flush()
                return proposal.id
        except Exception as e:
            logger.error(f"Failed to save proposal: {str(e)}")
            return -1


b2b_proposal_service = B2BProposalService()


# ============================================================================
# MODULE 3: IMPACT REPORTER SERVICE
# ============================================================================

class ImpactReporterService:
    """Service for AI-powered sustainability impact reporting."""
    
    async def generate_impact_report(self, order_id: int) -> Dict[str, Any]:
        """Generate impact report for an order."""
        # Get order details
        order = self._get_order_with_products(order_id)
        
        if not order:
            return {"success": False, "error": "Order not found"}
        
        # Calculate impact metrics
        metrics = self._calculate_impact_metrics(order)
        
        # Generate AI narrative
        narrative_result = await self._generate_impact_narrative(order, metrics)
        
        if narrative_result["success"]:
            metrics["narrative"] = narrative_result["narrative"]
            metrics["comparisons"] = narrative_result["comparisons"]
        
        # Save report
        report_id = self._save_impact_report(order_id, metrics)
        
        return {
            "success": True,
            "report_id": report_id,
            "data": metrics,
            "tokens_used": narrative_result.get("tokens_used", {}),
            "duration_ms": narrative_result.get("duration_ms", 0)
        }
    
    def _calculate_impact_metrics(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate environmental impact metrics."""
        plastic_saved = 0
        carbon_avoided = 0
        water_saved = 0
        local_items = 0
        total_items = len(order["items"])
        
        for item in order["items"]:
            product = item.get("product_data", {})
            quantity = item.get("quantity", 1)
            
            # Plastic saved (kg)
            conventional_plastic = product.get("conventional_plastic_g", 0)
            product_plastic = product.get("product_plastic_g", 0)
            plastic_saved += (conventional_plastic - product_plastic) * quantity / 1000
            
            # Carbon footprint avoided (kg CO2)
            carbon_avoided += product.get("carbon_footprint_kg", 0) * quantity
            
            # Water saved (liters)
            water_saved += product.get("water_usage_liters", 0) * quantity
            
            # Local sourcing
            if product.get("local_sourced", False):
                local_items += 1
        
        local_percentage = (local_items / total_items * 100) if total_items > 0 else 0
        
        return {
            "plastic_saved_kg": round(plastic_saved, 2),
            "carbon_avoided_kg": round(carbon_avoided, 2),
            "water_saved_liters": round(water_saved, 2),
            "local_sourcing_percentage": round(local_percentage, 2),
            "total_items": total_items
        }
    
    async def _generate_impact_narrative(
        self,
        order: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate human-readable impact narrative using AI."""
        prompt = f"""Generate a compelling sustainability impact story for this order.

ORDER: {order.get('order_number')}
CUSTOMER: {order.get('customer_name')}

IMPACT METRICS:
- Plastic saved: {metrics['plastic_saved_kg']} kg
- Carbon avoided: {metrics['carbon_avoided_kg']} kg CO2
- Water saved: {metrics['water_saved_liters']} liters
- Local sourcing: {metrics['local_sourcing_percentage']}%

Create a 2-3 sentence impact statement that:
1. Highlights the most significant metric
2. Includes a relatable real-world comparison
3. Conveys the positive environmental impact
4. Sounds natural and engaging

Also provide 3 interesting comparisons (e.g., "equivalent to X plastic bottles", "same as Y trees planted")
"""
        
        system_prompt = """You are a sustainability storyteller who makes environmental impact data engaging and relatable.

Create compelling narratives that:
- Use concrete, relatable comparisons
- Emphasize positive impact
- Sound natural and warm
- Avoid technical jargon

Return JSON with:
{
  "narrative": "2-3 sentence impact story",
  "comparisons": ["comparison 1", "comparison 2", "comparison 3"]
}
"""
        
        result = await ai_client.generate_structured_json(
            prompt=prompt,
            system_prompt=system_prompt,
            expected_schema={"narrative": "string", "comparisons": ["string"]},
            module_name="impact_reporter",
            request_metadata={"order_id": order.get("id")}
        )
        
        if result["success"]:
            return {
                "success": True,
                "narrative": result["parsed_data"].get("narrative", ""),
                "comparisons": result["parsed_data"].get("comparisons", []),
                "tokens_used": result["tokens_used"],
                "duration_ms": result["duration_ms"]
            }
        else:
            return {
                "success": False,
                "narrative": "Your order made a positive environmental impact!",
                "comparisons": []
            }
    
    def _get_order_with_products(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Get order with product details."""
        try:
            with get_db_context() as db:
                order = db.query(Order).filter(Order.id == order_id).first()
                
                if not order:
                    return None
                
                # Enrich items with product data
                enriched_items = []
                for item in order.items:
                    product_id = item.get("product_id")
                    if product_id:
                        product = db.query(Product).filter(Product.id == product_id).first()
                        if product:
                            item["product_data"] = {
                                "conventional_plastic_g": product.conventional_plastic_g or 0,
                                "product_plastic_g": product.product_plastic_g or 0,
                                "carbon_footprint_kg": product.carbon_footprint_kg or 0,
                                "water_usage_liters": product.water_usage_liters or 0,
                                "local_sourced": product.local_sourced or False
                            }
                    enriched_items.append(item)
                
                return {
                    "id": order.id,
                    "order_number": order.order_number,
                    "customer_name": order.customer_name,
                    "items": enriched_items,
                    "total_amount": order.total_amount
                }
        except Exception as e:
            logger.error(f"Error fetching order: {str(e)}")
            return None
    
    def _save_impact_report(self, order_id: int, metrics: Dict[str, Any]) -> int:
        """Save impact report to database."""
        try:
            with get_db_context() as db:
                report_number = f"IMP-{datetime.now().strftime('%Y%m%d')}-{order_id:04d}"
                
                report = ImpactReport(
                    report_number=report_number,
                    order_id=order_id,
                    plastic_saved_kg=metrics.get("plastic_saved_kg", 0),
                    carbon_avoided_kg=metrics.get("carbon_avoided_kg", 0),
                    water_saved_liters=metrics.get("water_saved_liters", 0),
                    local_sourcing_percentage=metrics.get("local_sourcing_percentage", 0),
                    impact_narrative=metrics.get("narrative", ""),
                    comparisons=metrics.get("comparisons", [])
                )
                db.add(report)
                db.flush()
                return report.id
        except Exception as e:
            logger.error(f"Failed to save impact report: {str(e)}")
            return -1


impact_reporter_service = ImpactReporterService()


# ============================================================================
# MODULE 4: WHATSAPP BOT SERVICE
# ============================================================================

class WhatsAppBotService:
    """Service for AI-powered WhatsApp customer support."""
    
    ESCALATION_KEYWORDS = [
        "refund", "complaint", "angry", "disappointed", "terrible",
        "manager", "speak to someone", "call me", "unacceptable",
        "legal", "lawyer", "sue", "fraud"
    ]
    
    def __init__(self):
        self.return_policy = self._get_return_policy()
    
    async def process_message(
        self,
        from_number: str,
        message_text: str,
        message_sid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process incoming WhatsApp message and generate response."""
        intent = self._detect_intent(message_text)
        should_escalate, escalation_reason = self._should_escalate(message_text, intent)
        
        if should_escalate:
            response = self._generate_escalation_response(escalation_reason)
            bot_response = response["message"]
            ai_data = response
        else:
            ai_result = await self._generate_ai_response(
                message_text=message_text,
                intent=intent,
                from_number=from_number
            )
            bot_response = ai_result.get("response", "I apologize, but I'm having trouble processing your request. Please try again.")
            ai_data = ai_result
        
        conversation_id = self._log_conversation(
            from_number=from_number,
            message_text=message_text,
            bot_response=bot_response,
            intent=intent,
            escalated=should_escalate,
            escalation_reason=escalation_reason if should_escalate else None,
            ai_data=ai_data,
            message_sid=message_sid
        )
        
        return {
            "success": True,
            "response": bot_response,
            "intent": intent,
            "escalated": should_escalate,
            "conversation_id": conversation_id
        }
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message."""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["order", "tracking", "status", "where is", "shipped"]):
            return "order_status"
        
        if any(keyword in message_lower for keyword in ["return", "refund", "exchange", "cancel"]):
            return "return_policy"
        
        if any(keyword in message_lower for keyword in ["product", "item", "available", "stock"]):
            return "product_inquiry"
        
        if any(keyword in message_lower for keyword in ["shipping", "delivery", "courier"]):
            return "shipping_inquiry"
        
        return "general_inquiry"
    
    def _should_escalate(self, message: str, intent: str) -> tuple:
        """Determine if message should be escalated to human agent."""
        message_lower = message.lower()
        
        for keyword in self.ESCALATION_KEYWORDS:
            if keyword in message_lower:
                return True, f"Contains keyword: {keyword}"
        
        if intent == "return_policy" and "refund" in message_lower:
            return True, "Refund request requires human approval"
        
        return False, None
    
    async def _generate_ai_response(
        self,
        message_text: str,
        intent: str,
        from_number: str
    ) -> Dict[str, Any]:
        """Generate AI response based on intent."""
        context = await self._get_context_for_intent(message_text, intent, from_number)
        system_prompt = self._build_system_prompt(intent, context)
        
        user_prompt = f"""Customer Message: {message_text}

Please provide a helpful, friendly response based on the context provided."""
        
        result = await ai_client.generate_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            module_name="whatsapp_bot",
            request_metadata={"intent": intent, "from_number": from_number}
        )
        
        if result["success"]:
            return {
                "response": result["response"],
                "tokens_used": result["tokens_used"],
                "duration_ms": result["duration_ms"],
                "context": context
            }
        else:
            return {
                "response": "I apologize, but I'm having trouble processing your request right now. Please try again in a moment.",
                "error": result.get("error")
            }
    
    async def _get_context_for_intent(
        self,
        message: str,
        intent: str,
        from_number: str
    ) -> Dict[str, Any]:
        """Retrieve relevant context data based on intent."""
        context = {"intent": intent}
        
        if intent == "order_status":
            order_number = self._extract_order_number(message)
            
            if order_number:
                order_data = self._get_order_details(order_number)
                context["order"] = order_data
            else:
                recent_orders = self._get_recent_orders_by_phone(from_number)
                context["recent_orders"] = recent_orders
        
        elif intent == "return_policy":
            context["return_policy"] = self.return_policy
        
        return context
    
    def _build_system_prompt(self, intent: str, context: Dict[str, Any]) -> str:
        """Build system prompt based on intent and context."""
        base_prompt = """You are Rayeva's AI customer support assistant. You help customers with their queries about sustainable products and orders.

PERSONALITY:
- Friendly, helpful, and professional
- Passionate about sustainability
- Concise but warm (keep responses under 150 words)
- Use emojis sparingly and appropriately

GUIDELINES:
- Always be helpful and empathetic
- If you don't have specific information, be honest about it
- Encourage sustainable choices
- Never make up order or product information
"""
        
        if intent == "order_status":
            if context.get("order"):
                order = context["order"]
                return f"""{base_prompt}

CURRENT CONTEXT - ORDER DETAILS:
Order Number: {order.get('order_number')}
Status: {order.get('status')}
Tracking: {order.get('tracking_number', 'Not available yet')}
Estimated Delivery: {order.get('estimated_delivery', 'TBD')}
Items: {len(order.get('items', []))} items
Total: ₹{order.get('total_amount', 0):.2f}

Provide the order status information clearly and helpfully."""
            elif context.get("recent_orders"):
                return f"""{base_prompt}

CONTEXT: Customer has {len(context['recent_orders'])} recent orders.
Ask them which order they're inquiring about, or provide a summary of all recent orders."""
            else:
                return f"""{base_prompt}

CONTEXT: No order number found in message and no recent orders.
Politely ask for their order number (format: ORD-XXXXXX)."""
        
        elif intent == "return_policy":
            return f"""{base_prompt}

RETURN POLICY:
{context.get('return_policy', 'Standard 30-day return policy applies.')}

Explain the return policy clearly. If they want to initiate a return, let them know you're escalating to our team."""
        
        else:
            return f"""{base_prompt}

Provide helpful general information about Rayeva's sustainable products and services."""
    
    def _extract_order_number(self, message: str) -> Optional[str]:
        """Extract order number from message."""
        patterns = [
            r'ORD[-_]?\d{6}',
            r'#ORD\d{6}',
            r'order\s+(?:number|#)?\s*[:=]?\s*(ORD[-_]?\d{6})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(0).upper().replace("#", "").replace("_", "-")
        
        return None
    
    def _get_order_details(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Get order details from database."""
        try:
            with get_db_context() as db:
                order = db.query(Order).filter(Order.order_number == order_number).first()
                
                if order:
                    return {
                        "order_number": order.order_number,
                        "status": order.status,
                        "tracking_number": order.tracking_number,
                        "estimated_delivery": order.estimated_delivery.strftime("%B %d, %Y") if order.estimated_delivery else None,
                        "total_amount": order.total_amount,
                        "items": order.items,
                        "created_at": order.created_at.strftime("%B %d, %Y")
                    }
        except Exception as e:
            logger.error(f"Error fetching order: {str(e)}")
        
        return None
    
    def _get_recent_orders_by_phone(self, phone_number: str) -> list:
        """Get recent orders by phone number."""
        try:
            with get_db_context() as db:
                orders = db.query(Order).filter(
                    Order.customer_phone.like(f"%{phone_number[-10:]}%")
                ).order_by(Order.created_at.desc()).limit(3).all()
                
                return [
                    {
                        "order_number": order.order_number,
                        "status": order.status,
                        "total_amount": order.total_amount,
                        "created_at": order.created_at.strftime("%B %d, %Y")
                    }
                    for order in orders
                ]
        except Exception as e:
            logger.error(f"Error fetching orders by phone: {str(e)}")
        
        return []
    
    def _generate_escalation_response(self, reason: str) -> Dict[str, Any]:
        """Generate response for escalated cases."""
        return {
            "message": """I understand your concern and want to ensure you get the best assistance. 

I'm connecting you with our customer care team who will personally handle your request. You'll receive a call within 2 business hours.

In the meantime, you can also email us at support@rayeva.com with your order details.

Thank you for your patience! 🙏""",
            "escalated": True,
            "reason": reason
        }
    
    def _log_conversation(
        self,
        from_number: str,
        message_text: str,
        bot_response: str,
        intent: str,
        escalated: bool,
        escalation_reason: Optional[str],
        ai_data: Dict[str, Any],
        message_sid: Optional[str]
    ) -> int:
        """Log conversation to database."""
        try:
            with get_db_context() as db:
                conversation = WhatsAppConversation(
                    from_number=from_number,
                    to_number=settings.twilio_whatsapp_number,
                    message_sid=message_sid,
                    user_message=message_text,
                    bot_response=bot_response,
                    intent=intent,
                    ai_response_data=ai_data,
                    escalated=escalated,
                    escalation_reason=escalation_reason,
                    responded_at=datetime.utcnow()
                )
                db.add(conversation)
                db.flush()
                return conversation.id
        except Exception as e:
            logger.error(f"Failed to log conversation: {str(e)}")
            return -1
    
    def _get_return_policy(self) -> str:
        """Get return policy text."""
        return """**Rayeva Return Policy**

✅ 30-day return window from delivery
✅ Products must be unused and in original packaging
✅ Free return pickup for damaged/defective items
✅ Refund processed within 5-7 business days

❌ Not eligible: Personalized items, intimate care products

To initiate a return, our team will guide you through the process."""


whatsapp_bot_service = WhatsAppBotService()


# ============================================================================
# API MODELS (Pydantic)
# ============================================================================

class ProductInput(BaseModel):
    """Input model for product categorization."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    product_id: Optional[int] = None


class BatchProductInput(BaseModel):
    """Input model for batch categorization."""
    products: List[ProductInput]


class ProposalInput(BaseModel):
    """Input model for B2B proposal generation."""
    client_id: int
    budget: float = Field(..., gt=0)
    requirements: Dict[str, Any]


class ImpactReportInput(BaseModel):
    """Input model for impact report generation."""
    order_id: int


class MessageInput(BaseModel):
    """Input model for sending messages."""
    to_number: str
    message: str


# ============================================================================
# API ROUTES
# ============================================================================

# Module 1: Category Tagger Routes
category_router = APIRouter(prefix="/api/category-tagger", tags=["Module 1: Category Tagger"])


@category_router.post("/categorize")
async def categorize_product(product: ProductInput):
    """Categorize a single product using AI."""
    try:
        result = await category_tagger_service.categorize_product(
            product_name=product.name,
            product_description=product.description,
            product_id=product.product_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@category_router.post("/categorize/batch")
async def batch_categorize_products(batch: BatchProductInput):
    """Categorize multiple products in batch."""
    try:
        products_data = [
            {"name": p.name, "description": p.description, "id": p.product_id}
            for p in batch.products
        ]
        
        results = await category_tagger_service.batch_categorize(products_data)
        
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@category_router.get("/categories")
async def get_available_categories():
    """Get list of available product categories."""
    return {
        "categories": category_tagger_service.categories,
        "sustainability_filters": category_tagger_service.sustainability_filters
    }


# Module 2: B2B Proposal Routes
proposal_router = APIRouter(prefix="/api/b2b-proposal", tags=["Module 2: B2B Proposal Generator"])


@proposal_router.post("/generate")
async def generate_proposal(proposal_input: ProposalInput):
    """Generate a B2B procurement proposal using AI."""
    try:
        result = await b2b_proposal_service.generate_proposal(
            client_id=proposal_input.client_id,
            budget=proposal_input.budget,
            requirements=proposal_input.requirements
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@proposal_router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: int, db: Session = Depends(get_db)):
    """Get a specific proposal by ID."""
    proposal = db.query(B2BProposal).filter(B2BProposal.id == proposal_id).first()
    
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return {
        "id": proposal.id,
        "proposal_number": proposal.proposal_number,
        "client_id": proposal.client_id,
        "budget": proposal.budget,
        "total_cost": proposal.total_cost,
        "selected_products": proposal.selected_products,
        "sustainability_score": proposal.sustainability_score,
        "justification": proposal.ai_justification,
        "status": proposal.status,
        "created_at": proposal.created_at
    }


# Module 3: Impact Reporter Routes
impact_router = APIRouter(prefix="/api/impact-reporter", tags=["Module 3: Impact Reporter"])


@impact_router.post("/generate/{order_id}")
async def generate_impact_report(order_id: int):
    """Generate sustainability impact report for an order."""
    try:
        result = await impact_reporter_service.generate_impact_report(order_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@impact_router.get("/reports/{report_id}")
async def get_impact_report(report_id: int, db: Session = Depends(get_db)):
    """Get a specific impact report by ID."""
    report = db.query(ImpactReport).filter(ImpactReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "report_number": report.report_number,
        "order_id": report.order_id,
        "plastic_saved_kg": report.plastic_saved_kg,
        "carbon_avoided_kg": report.carbon_avoided_kg,
        "water_saved_liters": report.water_saved_liters,
        "local_sourcing_percentage": report.local_sourcing_percentage,
        "narrative": report.impact_narrative,
        "comparisons": report.comparisons,
        "created_at": report.created_at
    }


# Module 4: WhatsApp Bot Routes
whatsapp_router = APIRouter(prefix="/api/whatsapp-bot", tags=["Module 4: WhatsApp Bot"])

# Initialize Twilio client if available
twilio_client = None
if TWILIO_AVAILABLE and settings.twilio_account_sid and settings.twilio_auth_token:
    try:
        twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    except:
        pass


@whatsapp_router.post("/webhook")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    MessageSid: Optional[str] = Form(None)
):
    """Twilio WhatsApp webhook endpoint."""
    try:
        logger.info(f"Received WhatsApp message from {From}: {Body}")
        
        result = await whatsapp_bot_service.process_message(
            from_number=From,
            message_text=Body,
            message_sid=MessageSid
        )
        
        if TWILIO_AVAILABLE:
            resp = MessagingResponse()
            resp.message(result["response"])
            return str(resp)
        else:
            return {"message": result["response"]}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        if TWILIO_AVAILABLE:
            resp = MessagingResponse()
            resp.message("Sorry, I encountered an error. Please try again or contact support@rayeva.com")
            return str(resp)
        else:
            return {"error": str(e)}


@whatsapp_router.post("/test")
async def test_bot(message: str):
    """Test bot response without Twilio."""
    result = await whatsapp_bot_service.process_message(
        from_number="test:+910000000000",
        message_text=message,
        message_sid="TEST"
    )
    return result


@whatsapp_router.get("/stats")
async def get_bot_stats(db: Session = Depends(get_db)):
    """Get WhatsApp bot statistics."""
    total_conversations = db.query(func.count(WhatsAppConversation.id)).scalar()
    escalated_count = db.query(func.count(WhatsAppConversation.id)).filter(
        WhatsAppConversation.escalated == True
    ).scalar()
    
    intent_stats = db.query(
        WhatsAppConversation.intent,
        func.count(WhatsAppConversation.id)
    ).group_by(WhatsAppConversation.intent).all()
    
    return {
        "total_conversations": total_conversations or 0,
        "escalated_conversations": escalated_count or 0,
        "escalation_rate": f"{(escalated_count / total_conversations * 100):.2f}%" if total_conversations and total_conversations > 0 else "0%",
        "intent_distribution": {intent: count for intent, count in intent_stats}
    }


# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Configure logging
Path("logs").mkdir(exist_ok=True)

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    settings.log_file_path,
    rotation="500 MB",
    retention="10 days",
    level=settings.log_level
)

# Initialize FastAPI app
app = FastAPI(
    title="Rayeva AI Systems - All 4 Modules",
    description="Complete AI-powered platform for sustainable commerce automation with all 4 modules implemented",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(category_router)
app.include_router(proposal_router)
app.include_router(impact_router)
app.include_router(whatsapp_router)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting Rayeva AI Systems - All 4 Modules...")
    logger.info(f"Environment: {settings.api_environment}")
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        logger.info("All 4 modules ready: Category Tagger, B2B Proposal, Impact Reporter, WhatsApp Bot")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Rayeva AI Systems...")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Rayeva AI Systems - Complete Platform",
        "version": "2.0.0",
        "status": "operational",
        "modules": {
            "1_category_tagger": {
                "status": "active",
                "description": "AI-powered product categorization and tagging",
                "endpoints": "/api/category-tagger/*"
            },
            "2_b2b_proposal": {
                "status": "active",
                "description": "AI-powered B2B procurement proposal generation",
                "endpoints": "/api/b2b-proposal/*"
            },
            "3_impact_reporter": {
                "status": "active",
                "description": "AI-powered sustainability impact reporting",
                "endpoints": "/api/impact-reporter/*"
            },
            "4_whatsapp_bot": {
                "status": "active",
                "description": "AI-powered WhatsApp customer support",
                "endpoints": "/api/whatsapp-bot/*"
            }
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "ai_service": "configured" if settings.anthropic_api_key else "not_configured",
        "modules_active": 4
    }


# ============================================================================
# DATABASE SEEDING FUNCTION
# ============================================================================

def seed_database():
    """Seed database with sample data."""
    logger.info("Seeding database with sample data...")
    
    products = [
        {
            "name": "Bamboo Toothbrush Set (4 Pack)",
            "description": "Eco-friendly bamboo toothbrushes with biodegradable bristles. Plastic-free alternative to conventional toothbrushes.",
            "price": 299.00,
            "sku": "BTB-001",
            "is_active": True,
            "conventional_plastic_g": 20,
            "product_plastic_g": 0,
            "carbon_footprint_kg": 0.5,
            "water_usage_liters": 10,
            "local_sourced": True
        },
        {
            "name": "Stainless Steel Reusable Straws",
            "description": "Set of 4 stainless steel straws with cleaning brush. Durable, dishwasher safe, and plastic-free.",
            "price": 199.00,
            "sku": "SSS-001",
            "is_active": True,
            "conventional_plastic_g": 5,
            "product_plastic_g": 0,
            "carbon_footprint_kg": 0.2,
            "water_usage_liters": 5,
            "local_sourced": False
        },
        {
            "name": "Organic Cotton Tote Bag",
            "description": "Large organic cotton tote bag. Perfect replacement for plastic shopping bags. Fair-trade certified.",
            "price": 399.00,
            "sku": "OCT-001",
            "is_active": True,
            "conventional_plastic_g": 50,
            "product_plastic_g": 0,
            "carbon_footprint_kg": 1.0,
            "water_usage_liters": 20,
            "local_sourced": True
        }
    ]
    
    orders = [
        {
            "order_number": "ORD-100001",
            "customer_name": "Priya Sharma",
            "customer_email": "priya@example.com",
            "customer_phone": "+919876543210",
            "total_amount": 897.00,
            "items": [
                {"product_id": 1, "product": "Bamboo Toothbrush Set", "quantity": 2, "price": 299.00},
                {"product_id": 2, "product": "Stainless Steel Straws", "quantity": 1, "price": 199.00}
            ],
            "shipping_address": "123 MG Road, Bangalore, Karnataka 560001",
            "status": "shipped",
            "tracking_number": "TRK-98765432",
            "estimated_delivery": datetime.now() + timedelta(days=2)
        }
    ]
    
    clients = [
        {
            "name": "Green Office Solutions Pvt Ltd",
            "industry": "Corporate",
            "contact_email": "procurement@greenoffice.com",
            "contact_phone": "+919876543211"
        }
    ]
    
    with get_db_context() as db:
        for product_data in products:
            if not db.query(Product).filter(Product.sku == product_data.get("sku")).first():
                product = Product(**product_data)
                db.add(product)
        
        for order_data in orders:
            if not db.query(Order).filter(Order.order_number == order_data["order_number"]).first():
                order = Order(**order_data)
                db.add(order)
        
        for client_data in clients:
            if not db.query(B2BClient).filter(B2BClient.name == client_data["name"]).first():
                client = B2BClient(**client_data)
                db.add(client)
    
    logger.info("Database seeding completed!")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Seed database on startup
    try:
        seed_database()
    except Exception as e:
        logger.warning(f"Could not seed database: {str(e)}")
    
    # Run the application
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    logger.info("All 4 modules active and ready!")
    
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower()
    )