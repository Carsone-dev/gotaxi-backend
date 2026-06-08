from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.core.logging import configure_logging
from app.exceptions import GoTaxiException, gotaxi_exception_handler
from app.routers import auth, users, voyages, reservations, colis, public, admin
from app.routers.chauffeurs import router as chauffeurs_router
from app.routers.wallet import router as wallet_router
from app.routers.transactions import router as transactions_router
from app.routers.avis import router as avis_router
from app.routers.notifications import router as notifications_router
from app.websockets.tracking import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.DEBUG)
    yield


app = FastAPI(
    title="GoTaxi API",
    version="1.0.0",
    description="API backend GoTaxi — transport interurbain & livraison de colis",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(GoTaxiException, gotaxi_exception_handler)

_media_dir = Path(__file__).resolve().parents[1] / "media"
_media_dir.mkdir(exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")

prefix = settings.API_V1_PREFIX
app.include_router(public.router, prefix=prefix)
app.include_router(auth.router, prefix=prefix)
app.include_router(users.router, prefix=prefix)
app.include_router(chauffeurs_router, prefix=prefix)
app.include_router(voyages.router, prefix=prefix)
app.include_router(reservations.router, prefix=prefix)
app.include_router(colis.router, prefix=prefix)
app.include_router(wallet_router, prefix=prefix)
app.include_router(transactions_router, prefix=prefix)
app.include_router(avis_router, prefix=prefix)
app.include_router(notifications_router, prefix=prefix)
app.include_router(admin.router, prefix=prefix)
app.include_router(ws_router)