import React from 'react';
import { 
  Activity, 
  Database, 
  RefreshCw, 
  Zap, 
  Calendar, 
  MapPin, 
  ShieldCheck, 
  Globe2 
} from 'lucide-react';

export default function Header({ 
  activeTab, 
  setActiveTab, 
  isDbConnected, 
  lastUpdated, 
  onRefresh, 
  isLoading 
}) {
  const tabs = [
    { id: 'live', label: 'Temps Réel & Mix', icon: Zap },
    { id: 'monthly', label: 'Historique Mensuel', icon: Calendar },
    { id: 'capacities', label: 'Registre & Capacités', icon: MapPin },
    { id: 'quality', label: 'Audit Qualité (100%)', icon: ShieldCheck },
    { id: 'international', label: 'Banque Mondiale', icon: Globe2 },
  ];

  return (
    <header className="header-container glass-panel">
      <div className="header-top">
        {/* Logo & Identité Xamale */}
        <div className="brand-wrapper">
          <div className="logo-container">
            <img 
              src="/logo.png" 
              alt="Logo Xamale" 
              className="brand-logo"
            />
          </div>
          <div className="brand-text">
            <div className="brand-title-row">
              <span className="brand-name">XamaleEnergy</span>
              <span className="brand-tag">OBSERVATOIRE ÉNERGÉTIQUE</span>
            </div>
            <p className="brand-subtitle">
              Plateforme d'Architecture Analytique & Données Publiques de France (RTE • Enedis • Banque Mondiale)
            </p>
          </div>
        </div>

        {/* Diagnostic & Actions */}
        <div className="header-actions">
          {/* Badge Connectivité PostgreSQL */}
          <div className={`status-badge ${isDbConnected ? 'connected' : 'disconnected'}`}>
            <Database size={15} />
            <span>{isDbConnected ? 'PostgreSQL 16 Connecté' : 'Base de données hors ligne'}</span>
            <span className="live-pulse-dot" />
          </div>

          {/* Horodatage & Actualisation */}
          <div className="refresh-wrapper">
            {lastUpdated && (
              <span className="last-sync-text">
                Actualisé à {new Date(lastUpdated).toLocaleTimeString('fr-FR')}
              </span>
            )}
            <button 
              className="btn-primary refresh-button" 
              onClick={onRefresh} 
              disabled={isLoading}
              title="Rafraîchir les données en direct"
            >
              <RefreshCw size={15} className={isLoading ? 'spin-animation' : ''} />
              <span>{isLoading ? 'Synchronisation...' : 'Actualiser'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Barre de Navigation par Onglets */}
      <nav className="nav-tabs-container">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              className={`nav-tab-button ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              <Icon size={16} className="tab-icon" />
              <span>{tab.label}</span>
              {isActive && <div className="tab-active-indicator" />}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
