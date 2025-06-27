from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.rebalance import router as rebalance_router

app = FastAPI(
    title="IBKR Portfolio Rebalancer",
    description="FastAPI service for Interactive Brokers portfolio rebalancing",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rebalance_router, prefix="/api/v1", tags=["rebalance"])


@app.get("/")
async def root():
    return {"message": "IBKR Portfolio Rebalancer API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}