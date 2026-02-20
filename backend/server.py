from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Header
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import numpy as np
import numpy_financial as npf
import io
import xlsxwriter

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============= MODELS =============

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Company(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    sector: str
    beta: float
    market_cap: float  # in billions SAR
    current_price: float  # SAR
    dividend_yield: float  # as decimal
    dividend_growth: float  # as decimal
    earnings_growth: float  # as decimal
    exit_multiple: float

class AnalysisInput(BaseModel):
    investment_usd: float
    exit_year: int
    company_id: str

class YearlyCashFlow(BaseModel):
    year: int
    dividend: float
    discounted_value: float

class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    company: Company
    investment_usd: float
    investment_sar: float
    exit_year: int
    required_return: float
    yearly_dividends: List[YearlyCashFlow]
    terminal_value: float
    npv: float
    irr: float
    total_gain: float
    capital_gains_tax: float
    dividend_tax: float
    after_tax_return: float
    cap_classification: str
    risk_indicator: str
    created_at: datetime

class AnalysisSave(BaseModel):
    analysis: Dict[str, Any]

# ============= UTILITY FUNCTIONS =============

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != 'bearer':
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    return User(**user_doc)

def classify_market_cap(market_cap: float) -> str:
    """Classify company by market cap (in billions SAR)"""
    if market_cap >= 100:
        return "Large Cap"
    elif market_cap >= 10:
        return "Mid Cap"
    else:
        return "Small Cap"

def classify_risk(beta: float) -> str:
    """Classify risk based on beta"""
    if beta < 0.8:
        return "Low Risk"
    elif beta <= 1.2:
        return "Medium Risk"
    else:
        return "High Risk"

def calculate_capm(beta: float, rf: float, rm: float, crp: float) -> float:
    """Calculate required return using CAPM with country risk premium"""
    return rf + beta * (rm - rf) + crp

def calculate_irr(cash_flows: List[float]) -> float:
    """Calculate IRR using numpy_financial"""
    try:
        irr = npf.irr(cash_flows)
        return float(irr) if not np.isnan(irr) else 0.0
    except:
        return 0.0

# ============= ROUTES =============

@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
    
    # Create user
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "name": user_data.name,
        "password": hashed_password.decode('utf-8'),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Create token
    access_token = create_access_token(data={"sub": user_id})
    
    user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        created_at=datetime.now(timezone.utc)
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not bcrypt.checkpw(credentials.password.encode('utf-8'), user_doc['password'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create token
    access_token = create_access_token(data={"sub": user_doc['id']})
    
    user = User(
        id=user_doc['id'],
        email=user_doc['email'],
        name=user_doc['name'],
        created_at=datetime.fromisoformat(user_doc['created_at']) if isinstance(user_doc['created_at'], str) else user_doc['created_at']
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.get("/auth/profile", response_model=User)
async def get_profile(user: User = Depends(get_current_user)):
    return user

@api_router.get("/sectors")
async def get_sectors():
    sectors = await db.companies.distinct("sector")
    return {"sectors": sectors}

@api_router.get("/companies", response_model=List[Company])
async def get_companies(sector: Optional[str] = None):
    query = {}
    if sector:
        query["sector"] = sector
    
    companies = await db.companies.find(query, {"_id": 0}).to_list(1000)
    return companies

@api_router.get("/companies/{company_id}", response_model=Company)
async def get_company(company_id: str):
    company = await db.companies.find_one({"id": company_id}, {"_id": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@api_router.post("/analysis/calculate", response_model=AnalysisResult)
async def calculate_analysis(input_data: AnalysisInput):
    
    # Get company data
    company_doc = await db.companies.find_one({"id": input_data.company_id}, {"_id": 0})
    if not company_doc:
        raise HTTPException(status_code=404, detail="Company not found")
    
    company = Company(**company_doc)
    
    # Constants
    USD_SAR_RATE = 3.75
    RF = 0.05801  # Risk-free rate
    RM = 0.089335  # Market return
    CRP = 0.0078  # Country risk premium
    CAPITAL_GAINS_TAX_RATE = 0.20  # 20%
    DIVIDEND_TAX_RATE = 0.10  # 10%
    
    # Step 1: Convert investment
    investment_sar = input_data.investment_usd * USD_SAR_RATE
    
    # Step 2: Calculate required return using CAPM
    required_return = calculate_capm(company.beta, RF, RM, CRP)
    
    # Step 3: Calculate yearly dividends
    yearly_dividends = []
    annual_dividend_base = investment_sar * company.dividend_yield
    
    for year in range(1, input_data.exit_year + 1):
        dividend = annual_dividend_base * ((1 + company.dividend_growth) ** year)
        discount_factor = (1 + required_return) ** year
        discounted_value = dividend / discount_factor
        
        yearly_dividends.append(YearlyCashFlow(
            year=year,
            dividend=dividend,
            discounted_value=discounted_value
        ))
    
    # Step 4: Calculate terminal value
    num_shares = investment_sar / company.current_price
    future_earnings_per_share = company.current_price * ((1 + company.earnings_growth) ** input_data.exit_year)
    terminal_stock_price = future_earnings_per_share * company.exit_multiple
    terminal_value = num_shares * terminal_stock_price
    
    # Step 5: Construct cash flows for NPV and IRR
    cash_flows = [-investment_sar]  # Initial investment (negative)
    
    # Add dividends for years 1 to T-1
    for i in range(input_data.exit_year - 1):
        cash_flows.append(yearly_dividends[i].dividend)
    
    # Add final year dividend + terminal value
    if input_data.exit_year > 0:
        final_cash_flow = yearly_dividends[-1].dividend + terminal_value
        cash_flows.append(final_cash_flow)
    
    # Step 6: Calculate NPV and IRR
    npv_value = npf.npv(required_return, cash_flows)
    irr_value = calculate_irr(cash_flows)
    
    # Step 7: Calculate taxes
    total_dividends = sum([cf.dividend for cf in yearly_dividends])
    capital_gain = terminal_value - investment_sar
    
    capital_gains_tax = max(0, capital_gain * CAPITAL_GAINS_TAX_RATE)
    dividend_tax = total_dividends * DIVIDEND_TAX_RATE
    
    total_gain = capital_gain + total_dividends
    after_tax_gain = total_gain - capital_gains_tax - dividend_tax
    after_tax_return = (after_tax_gain / investment_sar) * 100
    
    # Step 8: Classify company
    cap_classification = classify_market_cap(company.market_cap)
    risk_indicator = classify_risk(company.beta)
    
    # Create analysis result
    analysis_id = str(uuid.uuid4())
    result = AnalysisResult(
        id=analysis_id,
        user_id=user.id,
        company=company,
        investment_usd=input_data.investment_usd,
        investment_sar=investment_sar,
        exit_year=input_data.exit_year,
        required_return=required_return,
        yearly_dividends=yearly_dividends,
        terminal_value=terminal_value,
        npv=npv_value,
        irr=irr_value,
        total_gain=total_gain,
        capital_gains_tax=capital_gains_tax,
        dividend_tax=dividend_tax,
        after_tax_return=after_tax_return,
        cap_classification=cap_classification,
        risk_indicator=risk_indicator,
        created_at=datetime.now(timezone.utc)
    )
    
    return result

@api_router.post("/analysis/save")
async def save_analysis(data: AnalysisSave, user: User = Depends(get_current_user)):
    
    analysis_doc = data.analysis.copy()
    analysis_doc['user_id'] = user.id
    analysis_doc['created_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.analyses.insert_one(analysis_doc)
    
    return {"message": "Analysis saved successfully", "id": analysis_doc.get('id')}

@api_router.get("/analysis/history")
async def get_analysis_history(user: User = Depends(get_current_user)):
    
    analyses = await db.analyses.find(
        {"user_id": user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"analyses": analyses}

@api_router.get("/analysis/{analysis_id}/export-excel")
async def export_excel(analysis_id: str, user: User = Depends(get_current_user)):
    
    # Get analysis from history
    analysis_doc = await db.analyses.find_one({"id": analysis_id, "user_id": user.id}, {"_id": 0})
    if not analysis_doc:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Create Excel file in memory
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Investment Analysis")
    
    # Add formats
    header_format = workbook.add_format({'bold': True, 'bg_color': '#d4af37', 'font_color': '#0f172a'})
    currency_format = workbook.add_format({'num_format': '#,##0.00'})
    percent_format = workbook.add_format({'num_format': '0.00%'})
    
    # Write headers and data
    row = 0
    worksheet.write(row, 0, "Saudi Equity Investment Analysis", header_format)
    row += 2
    
    worksheet.write(row, 0, "Company:", header_format)
    worksheet.write(row, 1, analysis_doc['company']['name'])
    row += 1
    
    worksheet.write(row, 0, "Sector:", header_format)
    worksheet.write(row, 1, analysis_doc['company']['sector'])
    row += 1
    
    worksheet.write(row, 0, "Investment (USD):", header_format)
    worksheet.write(row, 1, analysis_doc['investment_usd'], currency_format)
    row += 1
    
    worksheet.write(row, 0, "Investment (SAR):", header_format)
    worksheet.write(row, 1, analysis_doc['investment_sar'], currency_format)
    row += 1
    
    worksheet.write(row, 0, "Exit Year:", header_format)
    worksheet.write(row, 1, analysis_doc['exit_year'])
    row += 2
    
    worksheet.write(row, 0, "NPV (SAR):", header_format)
    worksheet.write(row, 1, analysis_doc['npv'], currency_format)
    row += 1
    
    worksheet.write(row, 0, "IRR:", header_format)
    worksheet.write(row, 1, analysis_doc['irr'], percent_format)
    row += 1
    
    worksheet.write(row, 0, "After-Tax Return:", header_format)
    worksheet.write(row, 1, analysis_doc['after_tax_return'] / 100, percent_format)
    row += 2
    
    # Yearly dividends table
    worksheet.write(row, 0, "Year", header_format)
    worksheet.write(row, 1, "Dividend (SAR)", header_format)
    worksheet.write(row, 2, "Discounted Value (SAR)", header_format)
    row += 1
    
    for dividend_data in analysis_doc['yearly_dividends']:
        worksheet.write(row, 0, dividend_data['year'])
        worksheet.write(row, 1, dividend_data['dividend'], currency_format)
        worksheet.write(row, 2, dividend_data['discounted_value'], currency_format)
        row += 1
    
    workbook.close()
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=analysis_{analysis_id}.xlsx"}
    )

# ============= SEED DATA =============

@api_router.post("/seed-data")
async def seed_data():
    # Check if data already exists
    existing_companies = await db.companies.count_documents({})
    if existing_companies > 0:
        return {"message": "Data already seeded"}
    
    # Seed companies based on Excel data
    companies_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "Saudi Aramco",
            "sector": "Energy",
            "beta": 0.922487,
            "market_cap": 6191.0,
            "current_price": 23.5,
            "dividend_yield": 0.045,
            "dividend_growth": 0.03,
            "earnings_growth": 0.085,
            "exit_multiple": 12.5
        },
        {
            "id": str(uuid.uuid4()),
            "name": "SABIC",
            "sector": "Energy",
            "beta": 0.970935,
            "market_cap": 170.25,
            "current_price": 95.0,
            "dividend_yield": 0.038,
            "dividend_growth": 0.025,
            "earnings_growth": 0.065,
            "exit_multiple": 10.0
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Saudi Kayan",
            "sector": "Energy",
            "beta": 0.954651,
            "market_cap": 8.4,
            "current_price": 16.5,
            "dividend_yield": 0.042,
            "dividend_growth": 0.028,
            "earnings_growth": 0.072,
            "exit_multiple": 9.5
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Yansab",
            "sector": "Energy",
            "beta": 0.935885,
            "market_cap": 15.3,
            "current_price": 54.0,
            "dividend_yield": 0.040,
            "dividend_growth": 0.027,
            "earnings_growth": 0.068,
            "exit_multiple": 10.5
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Advanced Petrochemical",
            "sector": "Energy",
            "beta": 0.92826,
            "market_cap": 6.614,
            "current_price": 58.0,
            "dividend_yield": 0.048,
            "dividend_growth": 0.032,
            "earnings_growth": 0.078,
            "exit_multiple": 9.0
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Al Rajhi Bank",
            "sector": "Financial Services",
            "beta": 0.88,
            "market_cap": 340.0,
            "current_price": 85.0,
            "dividend_yield": 0.035,
            "dividend_growth": 0.04,
            "earnings_growth": 0.095,
            "exit_multiple": 13.0
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Saudi Telecom (STC)",
            "sector": "Telecommunications",
            "beta": 0.75,
            "market_cap": 280.0,
            "current_price": 42.0,
            "dividend_yield": 0.055,
            "dividend_growth": 0.022,
            "earnings_growth": 0.055,
            "exit_multiple": 11.0
        },
        {
            "id": str(uuid.uuid4()),
            "name": "ACWA Power",
            "sector": "Utilities",
            "beta": 1.05,
            "market_cap": 95.0,
            "current_price": 320.0,
            "dividend_yield": 0.028,
            "dividend_growth": 0.045,
            "earnings_growth": 0.12,
            "exit_multiple": 15.0
        }
    ]
    
    await db.companies.insert_many(companies_data)
    
    return {"message": f"Seeded {len(companies_data)} companies successfully"}

# Add CORS middleware BEFORE including routes
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add root health check
@app.get("/")
async def root():
    return {"status": "healthy", "service": "Saudi Equity Nexus API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Include router
app.include_router(api_router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
