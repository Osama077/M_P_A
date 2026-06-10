import React from 'react';
import { Activity, ShieldCheck } from 'lucide-react';
import { AppProvider, PAGES, useAppContext, USER_ROLES } from './context/AppContext';
import Navigation from './components/Navigation';
import HomePage from './components/HomePage';
import PlayerList from './components/PlayerList';
import PlayerProfile from './components/PlayerProfile';
import PlayerAnimatedAnalysis from './components/PlayerAnimatedAnalysis';
import PlayerCompare from './components/PlayerCompare';
import APITester from './components/APITester';
import PlayerForecast from './components/PlayerForecast';
import PlayerSimilarity from './components/PlayerSimilarity';
import PlayerMomentum from './components/PlayerMomentum';
import PlayerAnomalies from './components/PlayerAnomalies';
import PlayerConsistency from './components/PlayerConsistency';
import TopPerformers from './components/TopPerformers';
import SquadOverview from './components/SquadOverview';
import SeasonTrends from './components/SeasonTrends';
import MatchLog from './components/MatchLog';
import TacticalBoard from './components/TacticalBoard';
import WhatsNewPage from './components/WhatsNewPage';
import CoachingInsights from './components/CoachingInsights';
import MatchPrediction from './components/MatchPrediction';

function AppLayout() {
  const { currentPage, selectedPlayerName, selectedPlayerId, selectedMatchId, userRole, navigate, openPlayerDashboard } = useAppContext();

  const showApiTester = userRole === USER_ROLES.ADMIN || userRole === USER_ROLES.ANALYST;

  const renderPlayerSubpage = () => {
    if (!selectedPlayerName) {
      return (
        <div className="surface p-8 text-center">
          <p className="text-sm text-slate-600">Select a player first from the Players section.</p>
        </div>
      );
    }
    switch (currentPage) {
      case PAGES.FORECAST:
        return <PlayerForecast playerId={selectedPlayerId} playerName={selectedPlayerName} />;
      case PAGES.SIMILARITY:
        return <PlayerSimilarity playerId={selectedPlayerId} playerName={selectedPlayerName} onSelectPlayer={openPlayerDashboard} />;
      case PAGES.MOMENTUM:
        return <PlayerMomentum playerId={selectedPlayerId} playerName={selectedPlayerName} />;
      case PAGES.ANOMALIES:
        return <PlayerAnomalies playerId={selectedPlayerId} playerName={selectedPlayerName} />;
      case PAGES.CONSISTENCY:
        return <PlayerConsistency playerId={selectedPlayerId} playerName={selectedPlayerName} />;
      case PAGES.DASHBOARD:
        return <PlayerProfile playerName={selectedPlayerName} initialMatchId={selectedMatchId} />;
      default:
        return null;
    }
  };

  return (
    <div className="page-shell">
      <Navigation />

      <main className="mx-auto w-full max-w-[90%] pb-10 pt-6 animate-in">
        {currentPage === PAGES.OVERVIEW && <HomePage onNavigate={navigate} />}

        {currentPage === PAGES.SQUAD_OVERVIEW && <SquadOverview />}

        {currentPage === PAGES.SEASON_TRENDS && <SeasonTrends />}

        {currentPage === PAGES.MATCH_LOG && <MatchLog />}

        {currentPage === PAGES.TACTICAL_BOARD && <TacticalBoard />}

        {currentPage === PAGES.PLAYERS && <PlayerList onSelectPlayer={openPlayerDashboard} />}

        {currentPage === PAGES.DASHBOARD && renderPlayerSubpage()}

        {currentPage === PAGES.FORECAST && renderPlayerSubpage()}

        {currentPage === PAGES.SIMILARITY && renderPlayerSubpage()}

        {currentPage === PAGES.MOMENTUM && renderPlayerSubpage()}

        {currentPage === PAGES.ANOMALIES && renderPlayerSubpage()}

        {currentPage === PAGES.CONSISTENCY && renderPlayerSubpage()}

        {currentPage === PAGES.ANIMATED && (
          selectedPlayerName ? (
            <PlayerAnimatedAnalysis playerName={selectedPlayerName} />
          ) : (
            <div className="surface p-8 text-center">
              <p className="text-sm text-slate-600">Select a player first from the Players section.</p>
            </div>
          )
        )}

        {currentPage === PAGES.COMPARISON && <PlayerCompare />}

        {currentPage === PAGES.API_TESTER && showApiTester && <APITester />}

        {currentPage === PAGES.TOP_PERFORMERS && (
          <TopPerformers onSelectPlayer={openPlayerDashboard} />
        )}

        {currentPage === PAGES.COACHING && (
          <CoachingInsights playerId={selectedPlayerId} playerName={selectedPlayerName} />
        )}

        {currentPage === PAGES.PREDICTION && (
          <MatchPrediction playerId={selectedPlayerId} playerName={selectedPlayerName} />
        )}

        {currentPage === PAGES.WHATS_NEW && <WhatsNewPage />}
      </main>

      <footer className="border-t border-white/60 bg-white/70 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[90%] flex-col items-center justify-between gap-3 py-5 text-xs text-slate-500 sm:flex-row">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4" />
            <span>Match Performance Analysis Platform</span>
          </div>
          <p className="flex items-center gap-1">
            <ShieldCheck className="h-4 w-4" />
            Production-ready UI with ML-driven insights
          </p>
        </div>
      </footer>
    </div>
  );
}

function App() {
  return (
    <AppProvider>
      <AppLayout />
    </AppProvider>
  );
}

export default App;
