"""
Eczanem — Eczane Stok Takip Sistemi
FastAPI backend with Jinja2 templates.
"""

from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uuid
import random

# ─── App Setup ────────────────────────────────────────────────
app = FastAPI(title="Eczanem", description="Eczane Stok Takip Sistemi")

BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# ─── Demo Data ────────────────────────────────────────────────
CATEGORIES = [
    {"id": "agri", "name": "Ağrı Kesici", "icon": "💊", "color": "#ef4444"},
    {"id": "vitamin", "name": "Vitamin & Takviye", "icon": "🧬", "color": "#f59e0b"},
    {"id": "cilt", "name": "Cilt Bakımı", "icon": "✨", "color": "#ec4899"},
    {"id": "soguk", "name": "Soğuk Algınlığı", "icon": "🤧", "color": "#3b82f6"},
    {"id": "sindirim", "name": "Sindirim", "icon": "💚", "color": "#22c55e"},
]

PHARMACIES = [
    {"id": "ecz-1", "name": "Merkez Eczanesi", "city": "İstanbul", "lat": 41.0082, "lng": 28.9784, "on_duty": False, "address": "Fatih, İstanbul"},
    {"id": "ecz-2", "name": "Sağlık Eczanesi", "city": "İstanbul", "lat": 41.0382, "lng": 28.9884, "on_duty": True, "address": "Beyoğlu, İstanbul"},
    {"id": "ecz-3", "name": "Güneş Eczanesi", "city": "Ankara", "lat": 39.9208, "lng": 32.8541, "on_duty": False, "address": "Çankaya, Ankara"},
    {"id": "ecz-4", "name": "Umut Eczanesi", "city": "İzmir", "lat": 38.4192, "lng": 27.1287, "on_duty": True, "address": "Konak, İzmir"},
    {"id": "ecz-5", "name": "Hayat Eczanesi", "city": "Antalya", "lat": 36.8969, "lng": 30.7133, "on_duty": False, "address": "Muratpaşa, Antalya"},
]

BASE_PRODUCTS = [
    {"id": "p1", "name": "Parol 500mg", "generic": "Parasetamol", "category": "agri", "price": 42.50, "prescription": False, "barcode": "8699536090108"},
    {"id": "p2", "name": "Nurofen 400mg", "generic": "İbuprofen", "category": "agri", "price": 67.90, "prescription": False, "barcode": "8699536090115"},
    {"id": "p3", "name": "C Vitamini 1000mg", "generic": "Askorbik Asit", "category": "vitamin", "price": 125.00, "prescription": False, "barcode": "8699536090146"},
    {"id": "p4", "name": "Avene Cicalfate", "generic": "Onarıcı Krem", "category": "cilt", "price": 320.00, "prescription": False, "barcode": "8699536090184"},
    {"id": "p5", "name": "Tylol Hot", "generic": "Parasetamol + Vitamin C", "category": "soguk", "price": 56.00, "prescription": False, "barcode": "8699536090207"},
    {"id": "p6", "name": "Rennie Tablet", "generic": "Kalsiyum Karbonat", "category": "sindirim", "price": 48.90, "prescription": False, "barcode": "8699536090221"},
]

# Generate random stock for each pharmacy
PRODUCTS = []
for p in BASE_PRODUCTS:
    for ph in PHARMACIES:
        # 20% chance to be out of stock
        stock_count = 0 if random.random() < 0.2 else random.randint(1, 50)
        prod = p.copy()
        prod["uid"] = f"{p['id']}-{ph['id']}"
        prod["pharmacy_id"] = ph["id"]
        prod["pharmacy_name"] = ph["name"]
        prod["stock"] = stock_count
        prod["min_stock"] = 5
        PRODUCTS.append(prod)

# Helper
def get_stock_status(product: dict) -> dict:
    stock = product["stock"]
    min_s = product["min_stock"]
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
        ep["category_info"] = cat_map.get(p["category"], {})
        ep["stock_status"] = get_stock_status(p)
        enriched.append(ep)
    return enriched

# ─── Page Routes ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    stats = {
        "total_pharmacies": len(PHARMACIES),
        "on_duty": sum(1 for p in PHARMACIES if p["on_duty"]),
        "total_products": len(BASE_PRODUCTS),
    }
    return templates.TemplateResponse("index.html", {
        "request": request,
        "pharmacies": PHARMACIES,
        "categories": CATEGORIES,
        "stats": stats,
    })

@app.get("/urunler", response_class=HTMLResponse)
async def products_page(
    request: Request,
    search: str = Query(default=""),
    category: str = Query(default=""),
    pharmacy: str = Query(default="")
):
    filtered = PRODUCTS
    if search:
        q = search.lower()
        filtered = [p for p in filtered if q in p["name"].lower() or q in p["generic"].lower()]
    if category:
        filtered = [p for p in filtered if p["category"] == category]
    if pharmacy:
        filtered = [p for p in filtered if p["pharmacy_id"] == pharmacy]

    enriched = enrich_products(filtered)
    
    selected_pharmacy = next((p for p in PHARMACIES if p["id"] == pharmacy), None)

    return templates.TemplateResponse("products.html", {
        "request": request,
        "products": enriched,
        "categories": CATEGORIES,
        "search": search,
        "active_category": category,
        "active_pharmacy": pharmacy,
        "selected_pharmacy": selected_pharmacy,
        "pharmacies": PHARMACIES,
        "total": len(filtered),
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    enriched = enrich_products(PRODUCTS)
    stats = {
        "total_products": len(PRODUCTS),
        "in_stock": sum(1 for p in PRODUCTS if p["stock"] > 0),
        "out_of_stock": sum(1 for p in PRODUCTS if p["stock"] == 0),
        "low_stock": sum(1 for p in PRODUCTS if 0 < p["stock"] <= p["min_stock"]),
        "total_value": sum(p["price"] * p["stock"] for p in PRODUCTS),
        "prescription_count": sum(1 for p in PRODUCTS if p["prescription"]),
    }
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "products": enriched,
        "categories": CATEGORIES,
        "stats": stats,
    })

# ─── API Endpoints ────────────────────────────────────────────
@app.get("/api/pharmacies")
async def api_pharmacies():
    return PHARMACIES

@app.get("/api/products")
async def api_products(
    search: str = Query(default=""),
    category: str = Query(default=""),
    pharmacy: str = Query(default="")
):
    filtered = PRODUCTS
    if search:
        q = search.lower()
        filtered = [p for p in filtered if q in p["name"].lower() or q in p["generic"].lower()]
    if category:
        filtered = [p for p in filtered if p["category"] == category]
    if pharmacy:
        filtered = [p for p in filtered if p["pharmacy_id"] == pharmacy]
    return enrich_products(filtered)
