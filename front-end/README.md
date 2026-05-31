# Match Performance Analysis - React Frontend

🎯 Modern React frontend for the Match Performance Analysis API. Features player dashboards, comparison tools, and comprehensive API testing interface.

## 📋 Features

- **🏠 Home Dashboard**: Overview of platform features and capabilities
- **👥 Player Browser**: Search and browse all players in the database
- **📊 Player Dashboard**: 9 interactive visualizations per player
  - Radar Chart (7 dimensions)
  - Trend Chart (performance over season)
  - Heatmap (positioning density)
  - Pass Map (pass accuracy visualization)
  - Score Breakdown (dimension breakdown)
  - VAEP Analysis (value contributed)
  - Position Comparison (vs. position avg)
  - Shooting Map (shots + xG)
  - Percentile Rankings (team/league/position)

- **⚖️ Player Comparison**: Compare up to 5 players side-by-side
- **🧪 API Testing**: Test all endpoints and view responses

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm installed
- FastAPI backend running on `http://localhost:8000`

### Installation

```bash
# 1. Navigate to front-end directory
cd front-end

# 2. Install dependencies
npm install

# 3. Create environment file
cp .env.example .env

# 4. Start development server
npm start
```

The app will open at `http://localhost:3000`

## 🔧 Configuration

Create a `.env` file in the `front-end` directory:

```env
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_ENV=development
```

## 📁 Project Structure

```
front-end/
├── public/
│   └── index.html                 # HTML template
├── src/
│   ├── api.js                     # API client (all endpoints)
│   ├── App.js                     # Main app component
│   ├── index.js                   # ReactDOM entry point
│   ├── index.css                  # Global styles
│   └── components/
│       ├── Navigation.js          # Top navigation bar
│       ├── HomePage.js            # Landing page
│       ├── PlayerList.js          # Player browser
│       ├── PlayerDashboard.js     # 9-chart dashboard
│       ├── PlayerComparison.js    # Player comparison
│       ├── APITester.js           # API testing interface
│       ├── LoadingSpinner.js      # Loading component
│       └── ErrorAlert.js          # Error notification
├── package.json                   # Dependencies
├── .env.example                   # Environment template
└── README.md                      # This file
```

## 📡 API Integration

### Endpoints Used

All endpoints are defined in `src/api.js`:

#### Player Endpoints
- `GET /player/list` - List all players
- `GET /player/dashboard/{name}` - Get player dashboard (9 charts)
- `GET /player/{id}/score` - Player score
- `GET /player/{id}/stats` - Player statistics
- `GET /player/{id}/history` - Player match history
- `GET /player/compare?player_ids=1,2,3` - Compare players

#### Team Endpoints
- `GET /team/{id}/summary` - Team summary
- `GET /team/{id}/heatmap` - Team heatmap data

#### Match Endpoints
- `GET /match/{id}/report` - Match report
- `GET /match/{id}/events` - Match events

#### Analysis Endpoints
- `POST /analyze/match/{id}` - Analyze specific match
- `POST /analyze/season` - Analyze full season

#### Benchmark Endpoints
- `GET /benchmark/{position}` - Position benchmarks

## 🎨 UI Components

### Navigation
- Server status indicator (online/offline)
- Quick navigation to all pages
- Real-time API health checks (every 30 seconds)

### Player Dashboard
- Player information card (name, position, overall score)
- Chart selector with 9 options
- Large chart view
- Grid view of all 9 charts

### Player Comparison
- Searchable player selection (up to 5)
- Real-time filtering
- Side-by-side comparison results
- Key metrics display

### API Tester
- Individual endpoint testing
- Bulk "Test All" functionality
- Response time measurement
- Success/error statistics
- Result history

## 🛠️ Development

### Available Scripts

```bash
# Start development server (port 3000)
npm start

# Build for production
npm build

# Run tests
npm test

# Eject configuration (not recommended)
npm eject
```

### Technologies Used

- **React 18**: UI framework
- **Axios**: HTTP client for API
- **Tailwind CSS**: Utility-first CSS framework
- **React Router**: Navigation (optional, for future expansion)

## 📊 Data Flow

```
Frontend Component
    ↓
API Client (src/api.js)
    ↓
Axios HTTP Request
    ↓
FastAPI Backend (http://localhost:8000/api/v1)
    ↓
Backend Processing (ML models, data loading)
    ↓
Response (JSON/base64 images)
    ↓
Component State Update
    ↓
UI Render
```

## 🐛 Troubleshooting

### Connection Errors

**Problem**: "Cannot reach API server"

**Solutions**:
1. Verify FastAPI backend is running: `http://localhost:8000`
2. Check `.env` file has correct `REACT_APP_API_URL`
3. Ensure backend and frontend are on same network
4. Check firewall settings

### Player Dashboard Not Loading

**Problem**: Dashboard shows empty charts

**Solutions**:
1. Verify player name spelling (case-sensitive)
2. Check backend has processed all player data
3. Run `py run_pipeline.py --mode pipeline` on backend
4. Check browser console for errors (F12)

### Comparison Not Working

**Problem**: Compare button disabled

**Solutions**:
1. Select at least 2 players
2. Select at most 5 players
3. Check API endpoint in browser dev tools

## "API Testing Dashboard" Usage

Use the API Testing Dashboard to:
1. ✅ Verify backend connectivity
2. ✅ Test individual endpoints
3. ✅ Check response times
4. ✅ View response structure
5. ✅ Debug API issues

### Test Scenario

1. Open "API Test" page
2. Click "Test All Endpoints"
3. Check success rate (aim for 100%)
4. View response times (typical: 100-500ms)
5. Verify data structure in results

## 📈 Performance Considerations

- Dashboard loads all 9 charts at once (may take 2-3 seconds)
- Comparison is lightweight (< 500ms response)
- API Testing shows backend performance metrics
- Images are base64 encoded (load directly)

## 🔒 Security Notes

- No authentication required (demo mode)
- API runs on localhost by default
- Environment file not committed to git
- CORS handled by FastAPI backend

## 📝 Common Use Cases

### Scenario 1: View Player Performance
1. Homepage → Browse Players
2. Search for "Messi"
3. Click player card
4. Dashboard auto-loads with 9 charts
5. Navigate between charts or view grid

### Scenario 2: Compare Two Strikers
1. Homepage → Compare Players
2. Search and select first player
3. Search and select second player
4. Click "Compare Players"
5. View side-by-side metrics

### Scenario 3: Test Backend Integration
1. Homepage → API Test
2. Select player name for dashboard test
3. Click "Test All Endpoints" or test individually
4. Verify success rate and response times
5. Check error details if any fail

## 🤝 Integration with .NET Backend

This React frontend can be deployed alongside the .NET backend:

```
.NET Backend (ASP.NET Core)
    ↓
FastAPI Python API (/api/v1)
    ↓
React Frontend (http://localhost:3000)
```

## 📚 Additional Resources

- [API Documentation](../TUTORIAL.txt)
- [Backend Setup Guide](../README.md)
- [FastAPI Docs](http://localhost:8000/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS](https://tailwindcss.com)

## 🎓 Learning Path

1. Start with HomePage to understand architecture
2. Explore PlayerList for search functionality
3. View PlayerDashboard to see data visualization
4. Use APITester to understand backend integration
5. Modify components to add custom features

## 💡 Future Enhancements

- [ ] Authentication & user accounts
- [ ] Bookmark favorite players
- [ ] Custom alerts for player performance
- [ ] Export reports (PDF/Excel)
- [ ] Real-time match updates
- [ ] Team heatmap visualization
- [ ] Match analysis viewer
- [ ] Advanced filtering options

## ⚙️ Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `REACT_APP_API_URL` | Backend API URL | `http://localhost:8000/api/v1` |
| `REACT_APP_ENV` | Environment | `development` \| `production` |

## 📞 Support

For issues or questions:
1. Check API status in Navigation bar
2. Use API Testing Dashboard to debug
3. Check browser console (F12 → Console)
4. Verify backend is running on correct port
5. Review backend logs for errors

---

**Last Updated**: March 30, 2026
**React Version**: 18.2.0
**Status**: ✅ Production Ready
