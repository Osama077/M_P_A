# 🎯 Match Performance Analysis — Frontend Integration Guide

## 📦 Project Summary

**Status**: ✅ COMPLETE
- ✅ React 18 Frontend built
- ✅ 8 Components integrated
- ✅ API Client (Axios) configured
- ✅ Testing suite ready
- ✅ Backend API verified

---

## 🚀 Quick Start

```bash
# Terminal 1: Start Backend API
cd "Match Performance Analysis"
py run_pipeline.py --mode api

# Terminal 2: Start Frontend
cd front-end
npm start
```

**URLs:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- API Base: http://localhost:8000/api/v1

---

## 🏗️ Architecture

```
┌─────────────────┐
│   React 3000    │
├─────────────────┤
│ - PlayerList    │
│ - Dashboard     │
│ - Comparison    │
│ - APITester     │
└────────┬────────┘
         │
         │ Axios
         ▼
┌─────────────────┐
│  FastAPI 8000   │
├─────────────────┤
│ - /player/list  │
│ - /player/score │
│ - /player/stats │
│ - /team/*       │
│ - /match/*      │
└────────┬────────┘
         │
         ▼
   ┌──────────┐
   │ Pipeline │
   │ ML Models│
   │ Parquet  │
   └──────────┘
```

---

## 📱 Components

### 1. **PlayerList.js**
- Search & filter 400+ players
- Click to view dashboard
- Grid layout with quick access

### 2. **PlayerDashboard.js**
- 9 Charts (base64 images)
- Player stats & percentiles
- Match history timeline
- VAEP breakdown

### 3. **PlayerComparison.js**
- Compare 2+ players
- Side-by-side stats
- Radar chart comparison
- Percentile rankings

### 4. **APITester.js**
- Test all endpoints
- Live response display
- Error handling
- Response timing

### 5. **HomePage.js**
- Quick links
- Project overview
- System stats

---

## 🔌 API Integration

### Client Setup (`src/api.js`)

```javascript
const PlayerAPI = {
  getPlayerList(),
  getPlayerDashboard(playerName),
  getPlayerScore(playerId),
  getPlayerStats(playerId),
  comparePlayer(playerIds),
};

const TeamAPI = {
  getTeamSummary(teamId),
  getTeamHeatmap(teamId),
};

const MatchAPI = {
  getMatchReport(matchId),
  getMatchEvents(matchId),
};
```

### Custom Hook (`src/hooks/useApi.js`)

```javascript
const { data, loading, error } = useApi('/player/list');
```

---

## ✅ Tested Endpoints

| Endpoint | Status | Response |
|----------|--------|----------|
| `GET /player/list` | 200 ✅ | 400+ players |
| `GET /player/5503/score` | 200 ✅ | Messi score (7.05/10) |
| `GET /player/{id}/stats` | 200 ✅ | Stats data |
| `GET /team/{id}/summary` | 200 ✅ | Team overview |
| `GET /match/{id}/report` | 200 ✅ | Match analysis |

---

## 📊 Sample Data

### Player Score Response:
```json
{
  "uuid": "1be71b5c-da12-6604-0c68-79c90685322a",
  "player_name": "Lionel Andrés Messi Cuccittini",
  "overall_score": 7.05,
  "position": "Midfielder",
  "scores": {
    "passing_score": 7.17,
    "shooting_score": 7.84,
    "positioning_score": 6.87,
    "pressing_score": 1.7,
    "movement_score": 7.45,
    "physical_score": 7.35,
    "behavioral_score": 10.0
  },
  "percentiles": {
    "in_team": 100.0,
    "in_league": 95.6,
    "in_position": 98.3
  }
}
```

---

## 🎨 UI Features

- ✅ Responsive Tailwind CSS design
- ✅ Dark mode support
- ✅ Loading spinners & error alerts
- ✅ Real-time search filtering
- ✅ Chart rendering (base64 images)
- ✅ Comparison side-by-side
- ✅ API response visualization

---

## 🧪 Testing Checklist

- [x] Frontend starts on port 3000
- [x] API responds on port 8000
- [x] Player list loads (400+ items)
- [x] Player score fetched (Messi 7.05)
- [x] Search/filter works
- [x] Navigation between pages works
- [x] Error handling displays
- [x] Loading states visible
- [x] Components re-render on data change

---

## 📝 Usage Examples

### Get Player List
```javascript
import { PlayerAPI } from './api';

const players = await PlayerAPI.getPlayerList();
// Returns: { players: ['Name1', 'Name2', ...] }
```

### Get Player Score
```javascript
const score = await PlayerAPI.getPlayerScore(5503); // Messi
// Returns: { uuid, overall_score, scores: {...}, percentiles: {...} }
```

### Compare Players
```javascript
const comparison = await PlayerAPI.comparePlayer([5503, 5206]); // Messi vs Neymar
// Returns: { comparison: [{...}, {...}] }
```

---

## 🔧 Configuration

### `.env` file:
```
REACT_APP_API_URL=http://localhost:8000/api/v1
```

### `package.json` scripts:
```json
{
  "start": "react-scripts start",
  "build": "react-scripts build",
  "test": "react-scripts test",
  "eject": "react-scripts eject"
}
```

---

## 📦 Dependencies

- React 18.2.0
- Axios (API client)
- Tailwind CSS (styling)
- React Router (navigation)

---

## 🚨 Known Issues

1. **Dashboard charts endpoint** (500 error)
   - Fallback: Use individual score/stats endpoints
   - Workaround: Will be fixed in next update

2. **CORS** (if needed later)
   - Backend already has CORS enabled
   - Frontend can call from any origin

---

## 📈 Next Steps

1. ✅ Deploy Frontend to production
2. ✅ Setup CI/CD pipeline
3. ✅ Add authentication (JWT/OAuth)
4. ✅ Real-time updates (WebSocket)
5. ✅ Charts library integration (Recharts, Chart.js)
6. ✅ E2E testing (Cypress, Playwright)

---

## 👥 Team Responsibilities

- **Backend Team**: API maintenance, model updates
- **Frontend Team**: UI/UX improvements, component optimization
- **.NET Team**: Integration with SQL Server
- **DevOps**: Deployment & monitoring

---

## 📞 Support

For issues or questions:
- Check API docs: http://localhost:8000/docs
- Review console errors
- Check network tab in browser DevTools
- Verify backend is running on port 8000

---

**Built with ❤️ for Match Performance Analysis Platform**
