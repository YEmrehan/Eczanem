"""
Eczanem — Eczane Stok Takip & Satış Sistemi
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
    {"id": "bebek", "name": "Anne & Bebek", "icon": "👶", "color": "#a78bfa"},
    {"id": "ortopedi", "name": "Ortopedi", "icon": "🦴", "color": "#06b6d4"},
    {"id": "diyabet", "name": "Diyabet", "icon": "🩸", "color": "#f97316"},
]

PRODUCTS = [
    {"id": str(uuid.uuid4()), "name": "Parol 500mg", "generic": "Parasetamol", "category": "agri", "price": 42.50, "stock": 120, "min_stock": 20, "prescription": False, "barcode": "8699536090108"},
    {"id": str(uuid.uuid4()), "name": "Nurofen 400mg", "generic": "İbuprofen", "category": "agri", "price": 67.90, "stock": 85, "min_stock": 15, "prescription": False, "barcode": "8699536090115"},
    {"id": str(uuid.uuid4()), "name": "Majezik 100mg", "generic": "Flurbiprofen", "category": "agri", "price": 54.00, "stock": 3, "min_stock": 10, "prescription": False, "barcode": "8699536090122"},
    {"id": str(uuid.uuid4()), "name": "Apranax Fort 550mg", "generic": "Naproksen Sodyum", "category": "agri", "price": 89.90, "stock": 0, "min_stock": 10, "prescription": True, "barcode": "8699536090139"},
    {"id": str(uuid.uuid4()), "name": "C Vitamini 1000mg", "generic": "Askorbik Asit", "category": "vitamin", "price": 125.00, "stock": 200, "min_stock": 30, "prescription": False, "barcode": "8699536090146"},
    {"id": str(uuid.uuid4()), "name": "D3 Vitamini 1000 IU", "generic": "Kolekalsiferol", "category": "vitamin", "price": 98.50, "stock": 150, "min_stock": 25, "prescription": False, "barcode": "8699536090153"},
    {"id": str(uuid.uuid4()), "name": "Supradyn Energy", "generic": "Multivitamin", "category": "vitamin", "price": 189.90, "stock": 45, "min_stock": 10, "prescription": False, "barcode": "8699536090160"},
    {"id": str(uuid.uuid4()), "name": "B12 Vitamini 1000mcg", "generic": "Siyanokobalamin", "category": "vitamin", "price": 76.00, "stock": 8, "min_stock": 15, "prescription": False, "barcode": "8699536090177"},
    {"id": str(uuid.uuid4()), "name": "Avene Cicalfate Krem", "generic": "Onarıcı Krem", "category": "cilt", "price": 320.00, "stock": 30, "min_stock": 5, "prescription": False, "barcode": "8699536090184"},
    {"id": str(uuid.uuid4()), "name": "La Roche-Posay Effaclar", "generic": "Yüz Temizleme Jeli", "category": "cilt", "price": 410.00, "stock": 22, "min_stock": 5, "prescription": False, "barcode": "8699536090191"},
    {"id": str(uuid.uuid4()), "name": "Tylol Hot", "generic": "Parasetamol + Vitamin C", "category": "soguk", "price": 56.00, "stock": 95, "min_stock": 20, "prescription": False, "barcode": "8699536090207"},
    {"id": str(uuid.uuid4()), "name": "Theraflu Extra", "generic": "Soğuk Algınlığı Kombinasyonu", "category": "soguk", "price": 78.50, "stock": 60, "min_stock": 15, "prescription": False, "barcode": "8699536090214"},
    {"id": str(uuid.uuid4()), "name": "Rennie Tablet", "generic": "Kalsiyum Karbonat", "category": "sindirim", "price": 48.90, "stock": 110, "min_stock": 20, "prescription": False, "barcode": "8699536090221"},
    {"id": str(uuid.uuid4()), "name": "Gaviscon Likit", "generic": "Sodyum Alginat", "category": "sindirim", "price": 134.00, "stock": 0, "min_stock": 10, "prescription": False, "barcode": "8699536090238"},
    {"id": str(uuid.uuid4()), "name": "Aptamil 1 Bebek Maması", "generic": "Bebek Devam Sütü", "category": "bebek", "price": 450.00, "stock": 40, "min_stock": 10, "prescription": False, "barcode": "8699536090245"},
    {"id": str(uuid.uuid4()), "name": "Prima Bebek Bezi No:3", "generic": "Bebek Bezi", "category": "bebek", "price": 289.90, "stock": 75, "min_stock": 15, "prescription": False, "barcode": "8699536090252"},
    {"id": str(uuid.uuid4()), "name": "Voltaren Emulgel", "generic": "Diklofenak", "category": "ortopedi", "price": 145.00, "stock": 55, "min_stock": 10, "prescription": False, "barcode": "8699536090269"},
    {"id": str(uuid.uuid4()), "name": "Glucophage 1000mg", "generic": "Metformin", "category": "diyabet", "price": 34.50, "stock": 180, "min_stock": 30, "prescription": True, "barcode": "8699536090276"},
]

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
    featured = enrich_products(PRODUCTS[:6])
    stats = {
        "total_products": len(PRODUCTS),
        "in_stock": sum(1 for p in PRODUCTS if p["stock"] > 0),
        "categories": len(CATEGORIES),
        "low_stock": sum(1 for p in PRODUCTS if 0 < p["stock"] <= p["min_stock"]),
    }
    return templates.TemplateResponse("index.html", {
        "request": request,
        "featured": featured,
        "categories": CATEGORIES,
        "stats": stats,
    })


@app.get("/urunler", response_class=HTMLResponse)
async def products_page(
    request: Request,
    search: str = Query(default=""),
    category: str = Query(default=""),
):
    filtered = PRODUCTS
    if search:
        q = search.lower()
        filtered = [p for p in filtered if q in p["name"].lower() or q in p["generic"].lower()]
    if category:
        filtered = [p for p in filtered if p["category"] == category]

    enriched = enrich_products(filtered)
    return templates.TemplateResponse("products.html", {
        "request": request,
        "products": enriched,
        "categories": CATEGORIES,
        "search": search,
        "active_category": category,
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
    # Demo orders
    orders = [
        {"id": "SIP-001", "customer": "Ahmet Y.", "total": 298.50, "status": "Tamamlandı", "date": "04.05.2026", "items": 3},
        {"id": "SIP-002", "customer": "Fatma K.", "total": 125.00, "status": "Hazırlanıyor", "date": "04.05.2026", "items": 1},
        {"id": "SIP-003", "customer": "Mehmet D.", "total": 534.90, "status": "Beklemede", "date": "03.05.2026", "items": 4},
        {"id": "SIP-004", "customer": "Ayşe S.", "total": 89.90, "status": "Tamamlandı", "date": "03.05.2026", "items": 1},
        {"id": "SIP-005", "customer": "Can B.", "total": 410.00, "status": "İptal", "date": "02.05.2026", "items": 2},
    ]
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "products": enriched,
        "categories": CATEGORIES,
        "stats": stats,
        "orders": orders,
    })


# ─── API Endpoints ────────────────────────────────────────────
@app.get("/api/products")
async def api_products(
    search: str = Query(default=""),
    category: str = Query(default=""),
):
    filtered = PRODUCTS
    if search:
        q = search.lower()
        filtered = [p for p in filtered if q in p["name"].lower() or q in p["generic"].lower()]
    if category:
        filtered = [p for p in filtered if p["category"] == category]
    return enrich_products(filtered)


@app.get("/api/stats")
async def api_stats():
    return {
        "total_products": len(PRODUCTS),
        "in_stock": sum(1 for p in PRODUCTS if p["stock"] > 0),
        "out_of_stock": sum(1 for p in PRODUCTS if p["stock"] == 0),
        "total_value": sum(p["price"] * p["stock"] for p in PRODUCTS),
    }
