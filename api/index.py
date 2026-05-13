"""
Eczanem — Buse Eczanesi Stok Takip Sistemi
FastAPI backend with Jinja2 templates.
Single pharmacy mode with admin authentication.
"""

from fastapi import FastAPI, Request, Query, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
import json
import os
import uuid
from datetime import datetime
from hashlib import sha256
import hmac
import base64

# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(title="Eczanem", description="Buse Eczanesi Stok Takip Sistemi")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ─── Auth Config ──────────────────────────────────────────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "buse")
COOKIE_SECRET = os.environ.get("COOKIE_SECRET", "eczanem-buse-secret-key-2026")
COOKIE_NAME = "eczanem_auth"

def create_auth_token() -> str:
    """Create a signed auth cookie value."""
    payload = "admin:true"
    signature = hmac.new(COOKIE_SECRET.encode(), payload.encode(), sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()
    return token

def verify_auth_token(token: str) -> bool:
    """Verify a signed auth cookie."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        payload, signature = decoded.rsplit("|", 1)
        expected = hmac.new(COOKIE_SECRET.encode(), payload.encode(), sha256).hexdigest()
        return hmac.compare_digest(signature, expected) and payload == "admin:true"
    except Exception:
        return False

def is_admin(request: Request) -> bool:
    """Check if request has valid admin cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    return verify_auth_token(token)

# ─── Middleware: inject is_admin into all template contexts ───
class AdminContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.is_admin = is_admin(request)
        response = await call_next(request)
        return response

app.add_middleware(AdminContextMiddleware)

# ─── Pharmacy Data ────────────────────────────────────────────
PHARMACY = {
    "id": "buse-eczanesi",
    "name": "Buse Eczanesi",
    "city": "Bartın",
    "district": "MERKEZ",
    "lat": 41.6344,
    "lng": 32.3375,
    "on_duty": False,
    "address": "Merkez, Bartın",
    "phone": ""
}

# ─── Categories ───────────────────────────────────────────────
CATEGORIES = [
    {"id": "agri", "name": "Ağrı Kesici", "icon": "💊", "color": "#ef4444"},
    {"id": "vitamin", "name": "Vitamin & Takviye", "icon": "🧬", "color": "#f59e0b"},
    {"id": "cilt", "name": "Cilt Bakımı", "icon": "✨", "color": "#ec4899"},
    {"id": "soguk", "name": "Soğuk Algınlığı", "icon": "🤧", "color": "#3b82f6"},
    {"id": "sindirim", "name": "Sindirim", "icon": "💚", "color": "#22c55e"},
    {"id": "antibiyotik", "name": "Antibiyotik", "icon": "💉", "color": "#8b5cf6"},
    {"id": "alerji", "name": "Alerji", "icon": "🌿", "color": "#06b6d4"},
    {"id": "tansiyon", "name": "Tansiyon / Kalp", "icon": "❤️", "color": "#e11d48"},
    {"id": "diyabet", "name": "Diyabet", "icon": "🩸", "color": "#d97706"},
    {"id": "goz", "name": "Göz", "icon": "👁️", "color": "#0ea5e9"},
    {"id": "bebek", "name": "Anne & Bebek", "icon": "👶", "color": "#f472b6"},
    {"id": "agiz", "name": "Ağız & Diş", "icon": "🦷", "color": "#14b8a6"},
]

# ─── Products Data (File-based persistence) ──────────────────
PRODUCTS_FILE = os.path.join(BASE_DIR, 'data', 'products.json')

def load_products() -> list:
    """Load products from JSON file."""
    try:
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_products(products: list):
    """Save products to JSON file with atomic write."""
    temp_path = PRODUCTS_FILE + '.tmp'
    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, PRODUCTS_FILE)

# Helper
def get_stock_status(product: dict) -> dict:
    stock = product.get("stock", 0)
    min_s = product.get("min_stock", 5)
    if stock == 0:
        return {"label": "Tükendi", "class": "stock-out", "level": 0}
    elif stock <= min_s:
        return {"label": "Kritik Stok", "class": "stock-low", "level": 1}
    else:
        return {"label": "Stokta", "class": "stock-ok", "level": 2}

def enrich_products(products: list) -> list:
    cat_map = {c["id"]: c for c in CATEGORIES}
    enriched = []
    for p in products:
        ep = {**p}
        ep["category_info"] = cat_map.get(p.get("category", ""), {})
        ep["stock_status"] = get_stock_status(p)
        enriched.append(ep)
    return enriched

# ─── Template Context Helper ─────────────────────────────────
def tpl_context(request: Request, **kwargs):
    """Build template context with is_admin injected."""
    ctx = {"request": request, "is_admin": request.state.is_admin, "pharmacy": PHARMACY}
    ctx.update(kwargs)
    return ctx

# ─── Page Routes ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    products = load_products()
    
    # Featured products: in-stock items, limited
    featured = [p for p in products if p.get("stock", 0) > 0][:8]
    enriched_featured = enrich_products(featured)
    
    stats = {
        "total_products": len(products),
        "in_stock": sum(1 for p in products if p.get("stock", 0) > 0),
        "out_of_stock": sum(1 for p in products if p.get("stock", 0) == 0),
        "categories": len(CATEGORIES),
    }
    
    return templates.TemplateResponse("index.html", tpl_context(
        request,
        categories=CATEGORIES,
        featured_products=enriched_featured,
        stats=stats,
    ))

@app.get("/urunler", response_class=HTMLResponse)
async def products_page(
    request: Request,
    search: str = Query(default=""),
    category: str = Query(default=""),
):
    products = load_products()
    
    filtered = products
    if search:
        q = search.lower()
        filtered = [p for p in filtered if q in p["name"].lower() or q in p.get("generic", "").lower()]
    if category:
        filtered = [p for p in filtered if p.get("category") == category]

    total_count = len(filtered)
    enriched = enrich_products(filtered)

    return templates.TemplateResponse("products.html", tpl_context(
        request,
        products=enriched,
        categories=CATEGORIES,
        search=search,
        active_category=category,
        total=total_count,
    ))

# ─── Auth Routes ──────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = Query(default="")):
    if is_admin(request):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse("login.html", tpl_context(
        request,
        error=error,
    ))

@app.post("/login")
async def login_submit(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        response = RedirectResponse("/admin", status_code=303)
        token = create_auth_token()
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
        )
        return response
    return RedirectResponse("/login?error=wrong", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response

# ─── Admin Routes ─────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    if not is_admin(request):
        return RedirectResponse("/login", status_code=303)
    
    products = load_products()
    
    stats = {
        "total_products": len(products),
        "in_stock": sum(1 for p in products if p.get("stock", 0) > 0),
        "out_of_stock": sum(1 for p in products if p.get("stock", 0) == 0),
        "low_stock": sum(1 for p in products if 0 < p.get("stock", 0) <= p.get("min_stock", 5)),
        "total_value": sum(p.get("price", 0) * p.get("stock", 0) for p in products),
        "prescription_count": sum(1 for p in products if p.get("prescription", False)),
    }
    
    enriched = enrich_products(products)

    return templates.TemplateResponse("admin.html", tpl_context(
        request,
        products=enriched,
        categories=CATEGORIES,
        stats=stats,
    ))

# ─── Admin API (CRUD) ────────────────────────────────────────

@app.post("/api/products", response_class=JSONResponse)
async def api_add_product(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    
    data = await request.json()
    products = load_products()
    
    new_product = {
        "id": f"p{uuid.uuid4().hex[:8]}",
        "name": data.get("name", "").strip(),
        "generic": data.get("generic", "").strip(),
        "category": data.get("category", ""),
        "price": float(data.get("price", 0)),
        "stock": int(data.get("stock", 0)),
        "min_stock": int(data.get("min_stock", 5)),
        "prescription": bool(data.get("prescription", False)),
        "barcode": data.get("barcode", "").strip(),
        "description": data.get("description", "").strip(),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }
    
    if not new_product["name"]:
        raise HTTPException(status_code=400, detail="Ürün adı gerekli")
    
    products.append(new_product)
    save_products(products)
    
    return {"success": True, "product": new_product}

@app.put("/api/products/{product_id}", response_class=JSONResponse)
async def api_update_product(request: Request, product_id: str):
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    
    data = await request.json()
    products = load_products()
    
    for i, p in enumerate(products):
        if p["id"] == product_id:
            products[i].update({
                "name": data.get("name", p["name"]).strip(),
                "generic": data.get("generic", p["generic"]).strip(),
                "category": data.get("category", p["category"]),
                "price": float(data.get("price", p["price"])),
                "stock": int(data.get("stock", p["stock"])),
                "min_stock": int(data.get("min_stock", p["min_stock"])),
                "prescription": bool(data.get("prescription", p["prescription"])),
                "barcode": data.get("barcode", p.get("barcode", "")).strip(),
                "description": data.get("description", p.get("description", "")).strip(),
            })
            save_products(products)
            return {"success": True, "product": products[i]}
    
    raise HTTPException(status_code=404, detail="Ürün bulunamadı")

@app.delete("/api/products/{product_id}", response_class=JSONResponse)
async def api_delete_product(request: Request, product_id: str):
    if not is_admin(request):
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    
    products = load_products()
    original_len = len(products)
    products = [p for p in products if p["id"] != product_id]
    
    if len(products) == original_len:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı")
    
    save_products(products)
    return {"success": True}

# ─── Public API ───────────────────────────────────────────────

@app.get("/api/products", response_class=JSONResponse)
async def api_products(
    search: str = Query(default=""),
    category: str = Query(default=""),
):
    products = load_products()
    
    if search:
        q = search.lower()
        products = [p for p in products if q in p["name"].lower() or q in p.get("generic", "").lower()]
    if category:
        products = [p for p in products if p.get("category") == category]
    
    return enrich_products(products)

@app.get("/api/pharmacy", response_class=JSONResponse)
async def api_pharmacy():
    return PHARMACY
