import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.database.session import engine, Base, SessionLocal
from backend.app.services.parking_service import ParkingService
from backend.app.services.websocket_manager import ws_manager
from backend.app.api.v1.router import api_router

logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed initial data
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ParkingService.seed_initial_data(db)
    finally:
        db.close()
    logger.info("Smart Parking System Backend started successfully.")
    yield
    # Shutdown
    logger.info("Smart Parking System Backend shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Smart Parking System (ESP32 + RFID + IoT + OpenCV AI)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include REST API router
app.include_router(api_router)

# WebSocket Realtime Endpoint
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Gửi lời chào và trạng thái ban đầu
        await websocket.send_json({
            "event_type": "CONNECTED",
            "message": "Connected to Smart Parking WebSocket Stream",
            "mode": "SIMULATION"
        })
        while True:
            # Giữ kết nối mở, lắng nghe tin nhắn ping/client commands nếu có
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

@app.get("/")
def root():
    return {
        "system": "Smart Parking System",
        "status": "RUNNING",
        "mode": "SIMULATION",
        "docs_url": "/docs",
        "slots_endpoint": "/api/v1/slots",
        "websocket_url": "/ws/live"
    }

@app.get("/health")
def health():
    return {"status": "HEALTHY", "simulation_active": True}
