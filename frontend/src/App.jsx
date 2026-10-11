import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import LiveMixTab from './components/LiveMixTab';
import MonthlyHistoryTab from './components/MonthlyHistoryTab';
import CapacitiesTab from './components/CapacitiesTab';
import QualityAuditTab from './components/QualityAuditTab';
import InternationalTab from './components/InternationalTab';
import { energyApi } from './api';
import './App.css';

export default function App() {
  const [activeTab, setActiveTab] = useState('live');
  const [isDbConnected, setIsDbConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Données des modules
  const [latestMetrics, setLatestMetrics] = useState(null);
  const [mixHistory, setMixHistory] = useState([]);
  const [historyRange, setHistoryRange] = useState(96); // 48h par défaut
  const [monthlyData, setMonthlyData] = useState([]);
  const [regionalData, setRegionalData] = useState([]);
  const [summaryData, setSummaryData] = useState(null);
  const [internationalData, setInternationalData] = useState([]);
  const [qualityReport, setQualityReport] = useState(null);

  // Fonction de chargement des données
  const loadData = useCallback(async (isSilent = false) => {
    if (!isSilent) setIsLoading(true);
    setError(null);

    try {
      // 1. Diagnostic de santé
      const health = await energyApi.getHealth().catch(() => ({ database_connected: false }));
      setIsDbConnected(health.database_connected);

      // 2. Métriques live & historique 30 min
      const [latest, history] = await Promise.all([
        energyApi.getLatestMetrics().catch(() => null),
        energyApi.getMixHistory(historyRange).catch(() => ({ points: [] })),
      ]);

      if (latest) setLatestMetrics(latest);
      if (history?.points) setMixHistory(history.points);

      // 3. Données des autres modules (chargées en parallèle)
      const [monthly, regional, summary, international, quality] = await Promise.all([
        energyApi.getMonthlyMix(null, 120).catch(() => ({ points: [] })),
        energyApi.getRegionalCapacities().catch(() => ({ items: [] })),
        energyApi.getCapacitiesSummary().catch(() => null),
        energyApi.getInternationalAccess().catch(() => ({ points: [] })),
        energyApi.getQualityReport(false).catch(() => null),
      ]);

      if (monthly?.points) setMonthlyData(monthly.points);
      if (regional?.items) setRegionalData(regional.items);
      if (summary) setSummaryData(summary);
      if (international?.points) setInternationalData(international.points);
      if (quality) setQualityReport(quality);

      setLastUpdated(new Date().toISOString());
    } catch (err) {
      console.error('Erreur de chargement global:', err);
      setError('Impossible de joindre le serveur API. Vérifiez que le backend FastAPI est démarré sur le port 8000.');
    } finally {
      setIsLoading(false);
    }
  }, [historyRange]);

  // Chargement initial et lors du changement de plage temporelle
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Actualisation automatique toutes les 60 secondes
  useEffect(() => {
    const interval = setInterval(() => {
      loadData(true);
    }, 60000);
    return () => clearInterval(interval);
  }, [loadData]);

  return (
    <div className="app-container">
      {/* En-tête avec Logo Xamale et Navigation */}
      <Header 
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isDbConnected={isDbConnected}
        lastUpdated={lastUpdated}
        onRefresh={() => loadData(false)}
        isLoading={isLoading}
      />

      {/* Message d'erreur s'il y a lieu */}
      {error && (
        <div className="error-banner glass-panel">
          <p>{error}</p>
          <button className="btn-secondary" onClick={() => loadData(false)}>Réessayer</button>
        </div>
      )}

      {/* Contenu de l'onglet actif */}
      <main className="main-content">
        {activeTab === 'live' && (
          <LiveMixTab 
            latestMetrics={latestMetrics}
            mixHistory={mixHistory}
            historyRange={historyRange}
            setHistoryRange={setHistoryRange}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'monthly' && (
          <MonthlyHistoryTab 
            monthlyData={monthlyData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'capacities' && (
          <CapacitiesTab 
            regionalData={regionalData}
            summaryData={summaryData}
            isLoading={isLoading}
          />
        )}

        {activeTab === 'quality' && (
          <QualityAuditTab 
            initialReport={qualityReport}
          />
        )}

        {activeTab === 'international' && (
          <InternationalTab 
            internationalData={internationalData}
            isLoading={isLoading}
          />
        )}
      </main>

      {/* Pied de page */}
      <footer className="footer-container">
        <div className="footer-content">
          <div className="footer-left">
            <span className="footer-brand">XAMALE • OBSERVATOIRE DES DONNÉES ÉNERGÉTIQUES</span>
            <p className="footer-desc">
              Architecture Data Engineering Médaillon (Bronze • Silver • Gold) & Pipeline Open Data officiel.
            </p>
          </div>
          <div className="footer-links">
            <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="footer-link">
              Documentation API Swagger
            </a>
            <span className="footer-separator">•</span>
            <span className="footer-credits">
              Sources : RTE éCO2mix • Enedis Registre 2025 • Banque Mondiale
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
