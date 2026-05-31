# Quick Reference Guide

## 🚀 2-Minute Quick Start

```bash
# 1. Install dependencies
cd front-end
npm install

# 2. Create environment file
cp .env.example .env

# 3. Verify backend is running on http://localhost:8000
# (In another terminal: py run_pipeline.py --mode api)

# 4. Start the frontend
npm start

# Done! Opens at http://localhost:3000
```

## 📋 Component Map

| Page | Component | Purpose |
|------|-----------|---------|
| Home | `HomePage.js` | Landing page with feature overview |
| Players | `PlayerList.js` | Browse and search all players |
| Dashboard | `PlayerDashboard.js` | 9 charts per player (radar, trend, etc) |
| Compare | `PlayerComparison.js` | Side-by-side player comparison |
| API Test | `APITester.js` | Test all endpoints |

## 🔗 API Endpoints Reference

### Player APIs
```javascript
await PlayerAPI.getPlayerList()                    // [✨ 0.1-0.2s]
await PlayerAPI.getPlayerDashboard(name)          // [⚡ 0.5-1.5s] - Slowest, generates 9 charts
await PlayerAPI.getPlayerScore(id)                // [✨ 0.1s]
await PlayerAPI.getPlayerStats(id)                // [✨ 0.2s]
await PlayerAPI.comparePlayer([1, 2, 3, ...])    // [✨ 0.3-0.5s]
```

### Dashboard Endpoint (Most Important)
```javascript
// Returns: { player_info, charts: { radar, trend, heatmap, ... } }
await PlayerAPI.getPlayerDashboard("Messi")
```

## 🧪 Test Scenarios

### Scenario 1: View Dashboard ✅
```
Home → Click "View Dashboard" 
  → Browse Players (👥)
    → Search "Messi"
      → Click player card
        → 9 charts load
```

### Scenario 2: Compare Players ✅
```
Home → Compare (⚖️)
  → Search player 1
    → Click +
      → Search player 2
        → Click +
          → Click "Compare Players"
            → See comparison
```

### Scenario 3: Test Endpoints ✅
```
Home → API Test (🧪)
  → Click "Test All Endpoints"
    → See results
      → Success rate should be ~100%
```

## 🛠️ File Editing

### Adding New Component
1. Create file in `src/components/NewComponent.js`
2. Import in `src/App.js`
3. Add route logic in `App.js`
4. Add navigation button in `Navigation.js`

### Adding New API Endpoint
1. Add method to `src/api.js` in appropriate API object
2. Use in component: `import { PlayerAPI } from '../api'`
3. Call: `await PlayerAPI.newMethod()`

### Styling
- Using Tailwind CSS classes directly in JSX
- No separate CSS files needed for components
- Global styles in `src/index.css`

## 📊 Component State Patterns

```javascript
// Loading + Error pattern (used in all components)
const [data, setData] = useState(null)
const [loading, setLoading] = useState(true)
const [error, setError] = useState(null)

useEffect(() => {
  const fetch = async () => {
    try {
      setLoading(true)
      const result = await SomeAPI.call()
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  fetch()
}, [dependency])

if (loading) return <LoadingSpinner />
if (error) return <ErrorAlert message={error} />
```

## 🎨 UI Components Available

```javascript
import LoadingSpinner from './LoadingSpinner'     // <LoadingSpinner message="..." />
import ErrorAlert from './ErrorAlert'             // <ErrorAlert message="..." />
import Navigation from './Navigation'             // <Navigation currentPage={page} onNavigate={...} />
```

## 🐛 Debugging Tips

### Check Server Status
```javascript
// In browser console:
const { HealthAPI } = await import('./src/api')
await HealthAPI.checkHealth()
```

### View API Response
- Open DevTools (F12)
- Network tab
- Click any request
- View Response + Preview

### Check Component Props
- React DevTools browser extension
- Inspect elements in component tree
- View props in sidebar

## 📱 Responsive Breakpoints

```
Mobile:     < 640px  (one column)
Tablet:     640-1024px  (two columns)
Desktop:    > 1024px  (three+ columns)
```

## ⚡ Performance Tips

- Dashboard endpoint is slowest (~1-1.5s) - being generated on the fly
- Player list caches after first load
- Comparison is fast (~0.3-0.5s)
- API Tester has 500ms delay between requests

## 🔑 Environment Variables

```bash
# In .env file:
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_ENV=development
```

## 📦 Dependencies Overview

| Package | Version | Purpose |
|---------|---------|---------|
| react | 18.2.0 | UI framework |
| axios | 1.6.0 | HTTP client |
| tailwindcss | 3.3.0 | Styling |
| react-router-dom | 6.20.0 | Routing (optional) |
| react-scripts | 5.0.1 | Build tools |

## 🎯 Common Tasks

### Add Loading To Button
```jsx
<button disabled={loading}>
  {loading ? '⏳ Loading...' : '🚀 Click Me'}
</button>
```

### Add Error Message
```jsx
{error && <ErrorAlert message={error} />}
```

### Add Loading State
```jsx
if (loading) return <LoadingSpinner message="Loading..." />
```

### Format Number
```javascript
value.toFixed(2)        // 2 decimals
value.toFixed(0)        // Integer
value.toString()        // String
```

### API Error Handling
```javascript
try {
  const data = await PlayerAPI.someMethod()
  // handle success
} catch (error) {
  setError(error.message)  // Shows in ErrorAlert
}
```

## 🚀 Deploy Commands

```bash
# Production build
npm run build           # Creates build/ folder

# Serve locally
npx serve -s build     # Serve at localhost:3000
```

## 🔗 Important URLs

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | React frontend |
| http://localhost:8000 | FastAPI backend |
| http://localhost:8000/docs | API Swagger docs |
| http://localhost:8000/redoc | API ReDoc docs |

## 📞 Quick Fixes

| Problem | Solution |
|---------|----------|
| Port 3000 in use | `npm start` will ask to use different port |
| Backend offline | Check http://localhost:8000 |
| CORS error | Backend CORS already configured |
| Chart not loading | Try different player name |
| API slow | Dashboard endpoint is slowest |

## 🎓 Learning Resources

- [React Hooks](https://react.dev/reference/react)
- [Tailwind Classes](https://tailwindcss.com/docs/utility-first)
- [Axios](https://axios-http.com/docs/intro)
- [Backend TUTORIAL](../TUTORIAL.txt)

## 💾 Saving Changes

All changes auto-update via hot reload:
- Save file (Ctrl+S)
- Browser auto-refreshes
- No manual restart needed

## ✅ Must-Try Features

1. **Search "Messi"** → View his dashboard
2. **Compare "Messi" vs "Neymar"** → See differences
3. **Run all API tests** → Check backend
4. **Try different player names** → See other dashboards
5. **Check response times** → Performance metrics

---

**Quick Links**:
- [Full Setup Guide](./SETUP.md)
- [README](./README.md)
- [Backend Tutorial](../TUTORIAL.txt)

