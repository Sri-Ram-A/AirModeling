from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.endpoints import dashboard
from app.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend for a dashboard-style air-quality attribution SaaS. It exposes "
        "station readings, transport matrix generation, and source inversion APIs."
    ),
    openapi_tags=[
        {
            "name": "dashboard",
            "description": "Data endpoints for the dashboard UI.",
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
router.include_router(dashboard.router, tags=["dashboard"])
app.include_router(router, prefix=settings.api_prefix)


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PromptMasters API</title>
        <style>
            body { 
                background-color: #0a0a0a; 
                color: #00ff41; 
                font-family: 'Courier New', Courier, monospace; 
                display: flex; 
                flex-direction: column; 
                align-items: center; 
                justify-content: center; 
                height: 100vh; 
                margin: 0;
                overflow: hidden;
            }
            .container {
                border: 1px solid #333;
                padding: 40px;
                background: #111;
                box-shadow: 0 0 20px rgba(0, 255, 65, 0.2);
                border-radius: 8px;
            }
            .ascii-art {
                font-weight: bold;
                line-height: 1.2;
                background: linear-gradient(90deg, #22c55e, #3b82f6, #a855f7, #22c55e);
                background-size: 300% 100%;
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                animation: gradientMove 5s linear infinite;
                font-size: 14px;
            }
            @keyframes gradientMove {
                0% { background-position: 0% 50%; }
                100% { background-position: 100% 50%; }
            }
            .status-bar {
                margin-top: 20px;
                padding: 10px;
                border-top: 1px solid #333;
                width: 100%;
                font-size: 0.9em;
                color: #888;
            }
            .dot {
                height: 10px;
                width: 10px;
                background-color: #22c55e;
                border-radius: 50%;
                display: inline-block;
                margin-right: 5px;
                box-shadow: 0 0 8px #22c55e;
            }
            a { color: #3b82f6; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <pre class="ascii-art">

                    ░█████╗░██╗██████╗░███╗░░░███╗░█████╗░██████╗░███████╗██╗░░░░░██╗███╗░░██╗░██████╗░
                    ██╔══██╗██║██╔══██╗████╗░████║██╔══██╗██╔══██╗██╔════╝██║░░░░░██║████╗░██║██╔════╝░
                    ███████║██║██████╔╝██╔████╔██║██║░░██║██║░░██║█████╗░░██║░░░░░██║██╔██╗██║██║░░██╗░
                    ██╔══██║██║██╔══██╗██║╚██╔╝██║██║░░██║██║░░██║██╔══╝░░██║░░░░░██║██║╚████║██║░░╚██╗
                    ██║░░██║██║██║░░██║██║░╚═╝░██║╚█████╔╝██████╔╝███████╗███████╗██║██║░╚███║╚██████╔╝
                    ╚═╝░░╚═╝╚═╝╚═╝░░╚═╝╚═╝░░░░░╚═╝░╚════╝░╚═════╝░╚══════╝╚══════╝╚═╝╚═╝░░╚══╝░╚═════╝░                                      
            </pre>
            <div class="status-bar">
                <span class="dot"></span> <strong>BACKEND ONLINE</strong> | 
                <a href="/docs">Interactive Docs</a> | 
                <a href="/redoc">Redoc</a>
            </div>
        </div>
    </body>
    </html>
    """
