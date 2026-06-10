import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import uvicorn
from api.main import app
uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
