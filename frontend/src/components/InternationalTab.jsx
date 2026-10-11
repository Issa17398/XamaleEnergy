import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { Globe2, Info, CheckCircle2 } from 'lucide-react';

export default function InternationalTab({ internationalData, isLoading }) {
  if (!internationalData || internationalData.length === 0) {
    return (
      <div className="tab-loading-state glass-panel">
        <Globe2 className="spin-animation icon-gold" size={32} />
        <p>Chargement des indicateurs de la Banque Mondiale...</p>
      </div>
    );
  }

  // Filtrage des points mesurés (1990 - 2022)
  const measuredPoints = internationalData.filter(d => !d.is_missing && d.valeur_pct !== null);

  return (
    <div className="tab-content-container fade-in">
      {/* Présentation */}
      <section className="glass-panel kpi-card highlight-gold">
        <div className="kpi-header">
          <span className="kpi-title">Indicateur International : Banque Mondiale</span>
          <div className="kpi-icon-badge gold">
            <Globe2 size={18} />
          </div>
        </div>
        <div className="kpi-value-row">
          <span className="kpi-main-number">100.0</span>
          <span className="kpi-unit">%</span>
        </div>
        <span className="kpi-subtext">
          Taux d'accès universel à l'électricité de la population française (Indicateur EG.ELC.ACCS.ZS)
        </span>
      </section>

      {/* Graphique */}
      <section className="chart-section glass-panel">
        <h3 className="section-heading">Historique d'Accès à l'Électricité en France (1990 - 2022)</h3>
        <p className="section-subheading">Série officielle consolidée issue de l'API Banque Mondiale</p>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={measuredPoints} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="annee" stroke="#64748B" fontSize={11} />
              <YAxis stroke="#64748B" fontSize={11} domain={[95, 100.5]} unit="%" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0A172C', borderColor: '#F5B82E', borderRadius: '10px' }}
                formatter={(val) => [`${val}%`, 'Taux d\'accès']}
              />
              <Line type="stepAfter" dataKey="valeur_pct" name="Taux d'accès (%)" stroke="#F5B82E" strokeWidth={3} dot={{ fill: '#F5B82E', r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Note méthodologique sur la rigueur Data Engineering */}
      <div className="physics-alert-box glass-panel">
        <div className="physics-alert-icon">
          <Info size={20} className="icon-gold" />
        </div>
        <div className="physics-alert-content">
          <h5 className="physics-title">Règle d'Intégrité : Gestion Explicite des Trous de Collecte</h5>
          <p className="physics-desc">
            La Banque Mondiale publie des séries de 1960 à 2025 (66 observations), mais les mesures formelles du taux d'électrification n'ont débuté qu'en 1990.
            Plutôt que d'extrapoler ou de supprimer ces lignes, notre pipeline Silver et Gold conserve les 66 enregistrements avec un drapeau explicite <code>is_missing = true</code> pour garantir la stricte reproductibilité scientifique.
          </p>
        </div>
      </div>
    </div>
  );
}
