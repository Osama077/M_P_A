# Frontend Setup & Installation Guide

## 📦 Prerequisites

Ensure you have installed:
- **Node.js** v16+ ([Download](https://nodejs.org))
- **npm** v8+ (comes with Node.js)
- **Backend running** on `http://localhost:8000`

Verify installation:
```bash
node --version    # Should be v16+
npm --version     # Should be v8+
```

## 🚀 Installation Steps

### Step 1: Navigate to Frontend Directory
```bash
cd front-end
```

### Step 2: Install Dependencies
```bash
npm install
```

This will install:
- React 18.2.0
- Axios 1.6.0
- Tailwind CSS 3.3.0
- React Router 6.20.0
- React Scripts 5.0.1

**Expected time**: 2-5 minutes

### Step 3: Configure Environment

Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` and set your backend URL:
```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_ENV=development
```

### Step 4: Start Development Server

```bash
npm start
```

Output should show:
```
Compiled successfully!

You can now view match-performance-frontend in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://YOUR_IP:3000

Note that the development build is not optimized.
To create a production build, use npm run build.
```

### Step 5: Open in Browser

Click the link or open: `http://localhost:3000`

## ✅ Verification Checklist

- [ ] Dependencies installed successfully
- [ ] No errors during `npm install`
- [ ] Environment file created (.env)
- [ ] Development server started (`npm start`)
- [ ] Browser opens to localhost:3000
- [ ] Navigation bar shows "✅ Server Online"
- [ ] Can click through different pages

## 🧪 Test the Frontend

### 1. Test Home Page
- ✅ Landing page loads with feature cards
- ✅ Can see "View Dashboard", "Compare Players", etc.

### 2. Test Player Browsing
- Click "👥 Players"
- ✅ Search box appears
- ✅ Click on a player (e.g., Messi)
- ✅ Should navigate to dashboard

### 3. Test Dashboard
- ✅ Player dashboard loads with 9 charts
- ✅ Can switch between charts
- ✅ Charts display as images
- ✅ Grid view shows all charts

### 4. Test Comparison
- Click "⚖️ Compare"
- ✅ Search for players
- ✅ Select 2-5 players
- ✅ Click "Compare Players"
- ✅ See comparison results

### 5. Test API Testing
- Click "🧪 API Test"
- ✅ Select a player name
- ✅ Click "🚀 Test All Endpoints"
- ✅ See test results
- ✅ Check success rate and response times

## 🔧 Common Issues & Solutions

### Issue: `npm install` fails

**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Try again
npm install
```

### Issue: Port 3000 already in use

**Solution**:
```bash
# Linux/Mac
lsof -ti:3000 | xargs kill -9

# Windows PowerShell
Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force
```

### Issue: "Cannot GET /api/v1/" in browser

**Solution**:
- Backend not running!
- Start backend: `py run_pipeline.py --mode api`
- Verify on `http://localhost:8000/docs`

### Issue: Player dashboard shows empty charts

**Solutions**:
1. Check player name spelling (case-sensitive)
2. Verify backend has processed data
3. Run: `py run_pipeline.py --mode pipeline`
4. Try a known player: "Messi"

### Issue: CORS errors in console

**Solution**:
- Backend CORS must allow localhost:3000
- Check backend `main.py` for CORS config
- Should already be configured

## 📊 Testing All Endpoints

Use the built-in **API Testing Dashboard**:

1. Navigate to **🧪 API Test**
2. Configure player name (default: "Messi")
3. Click **🚀 Test All Endpoints**
4. View results:
   - ✅ Green = Success
   - ❌ Red = Failed
   - Shows response times

### Expected Results

All 9 endpoints should succeed:
1. ✅ Health Check
2. ✅ Get Player List
3. ✅ Get Player Dashboard
4. ✅ Get Player Score
5. ✅ Get Player Stats
6. ✅ Compare Players
7. ✅ Get Team Summary
8. ✅ Get Match Report
9. ✅ Get Benchmark

## 📁 Project Structure After Setup

```
front-end/
├── node_modules/          # All dependencies (created after npm install)
├── public/
│   └── index.html         # HTML entry point
├── src/
│   ├── api.js             # API client
│   ├── App.js             # Main component
│   ├── components/        # All React components
│   ├── index.js           # React entry point
│   └── index.css          # Global styles
├── .env                   # Environment (created from .env.example)
├── .gitignore
├── package.json
├── package-lock.json      # Dependency versions (created after npm install)
└── README.md
```

## 🛠️ Development Commands

```bash
# Start development server (http://localhost:3000)
npm start

# Build for production (into build/ folder)
npm run build

# Run tests
npm test

# Clean build cache
npm cache clean --force

# Install specific version
npm install package-name@version
```

## 🌐 Backend Communication

Frontend communicates with FastAPI backend:

**Base URL**: `http://localhost:8000/api/v1`

**All requests go through**: `src/api.js`

Check `src/api.js` for all endpoint definitions:
```javascript
// Example: Player endpoints
PlayerAPI.getPlayerList()
PlayerAPI.getPlayerDashboard(playerName)
PlayerAPI.comparePlayer([id1, id2, id3])
```

## 📚 File-by-File Explanation

### `src/api.js` - API Client
Defines all HTTP calls to backend:
- `PlayerAPI` - All player endpoints
- `TeamAPI` - All team endpoints
- `MatchAPI` - All match endpoints
- `BenchmarkAPI` - Benchmark endpoints
- `AnalysisAPI` - Analysis endpoints

### `src/App.js` - Main Component
Routes between different pages

### `src/components/`
- `Navigation.js` - Top bar + server status
- `HomePage.js` - Landing page
- `PlayerList.js` - Browse players
- `PlayerDashboard.js` - 9-chart view
- `PlayerComparison.js` - Compare UI
- `APITester.js` - Endpoint testing
- `LoadingSpinner.js` - Loading indicator
- `ErrorAlert.js` - Error notification

## ✨ Features After Setup

✅ Browse all players
✅ Search players by name
✅ View 9-chart dashboard per player
✅ Compare up to 5 players
✅ Test all API endpoints
✅ View response times
✅ Real-time server status

## 🚀 Deployment (Optional)

### Build for Production
```bash
npm run build
```

This creates an optimized build in `build/` folder.

### Deploy to Server
```bash
# Copy build folder to web server
cp -r build/* /var/www/html/
```

## 🆘 Need Help?

1. Check browser console (F12 → Console tab)
2. Run "🧪 API Test" to verify connectivity
3. Check that backend is running: `http://localhost:8000`
4. Verify `.env` file has correct API URL
5. Try clearing npm cache: `npm cache clean --force`

## ✅ Completion Checklist

- [ ] Node.js installed (v16+)
- [ ] npm installed (v8+)
- [ ] `npm install` completed
- [ ] `.env` file created
- [ ] Backend running on localhost:8000
- [ ] `npm start` works
- [ ] localhost:3000 opens in browser
- [ ] Navigation shows "✅ Server Online"
- [ ] All 9 endpoints tested successfully
- [ ] Multiple players browsable
- [ ] Dashboard loads with charts
- [ ] Comparison works with 2+ players

Once all items checked, you're ready to use the frontend! 🎉

---

**Version**: 1.0.0
**Last Updated**: March 30, 2026
**Status**: ✅ Ready for Production
