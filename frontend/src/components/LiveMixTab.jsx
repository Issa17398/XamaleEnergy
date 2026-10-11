import React, { useState } from 'react';
import { 
  AreaChart, 
  Area, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts';
import { 
  Zap, 
  Atom, 
  Wind, 
  Sun, 
  Droplets, 
  Flame, 
  Leaf, 
  ArrowUpRight, 
  ArrowDownRight, 
  Sparkles,
  TrendingDown,
  Layers
} from 'lucide-react';

export default function LiveMixTab({ 
  latestMetrics, 
  mixHistory, 
  historyRange, 
  setHistoryRange, 
  isLoading 
}) {
  const [activeFiliere, setActiveFiliere] = useState(null);

  if (!latestMetrics) {
    return (
      <div className="tab-loading-state glass-panel">
        <Zap className="spin-animation icon-gold" size={32} />
        <p>Chargement des métriques du réseau électrique national...</p>
      </div>
    );
  }

  const { filieres, echanges } = latestMetrics;

  // Calcul des contributions pour chaque filière
  const totalProd = latestMetrics.production_totale_mw || 1;
  const filieresList = [
    { key: 'nucleaire_mw', name: 'Nucléaire', val: filieres.nucleaire_mw, color: 'var(--color-nucleaire)', icon: Atom, cat: 'Décarboné' },
    { key: 'hydraulique_mw', name: 'Hydraulique', val: filieres.hydraulique_mw, color: 'var(--color-hydraulique)', icon: Droplets, cat: 'Renouvelable' },
    { key: 'eolien_mw', name: 'Éolien', val: filieres.eolien_mw, color: 'var(--color-eolien)', icon: Wind, cat: 'Renouvelable' },
    { key: 'solaire_mw', name: 'Solaire', val: filieres.solaire_mw, color: 'var(--color-solaire)', icon: Sun, cat: 'Renouvelable' },
    { key: 'bioenergies_mw', name: 'Bioénergies', val: filieres.bioenergies_mw, color: 'var(--color-bioenergies)', icon: Leaf, cat: 'Renouvelable' },
    { key: 'gaz_mw', name: 'Gaz', val: filieres.gaz_mw, color: 'var(--color-gaz)', icon: Flame, cat: 'Fossile' },
    { key: 'fioul_mw', name: 'Fioul', val: filieres.fioul_mw, color: 'var(--color-fioul)', icon: Flame, cat: 'Fossile' },
    { key: 'charbon_mw', name: 'Charbon', val: filieres.charbon_mw, color: 'var(--color-charbon)', icon: Flame, cat: 'Fossile' },
  ];

  // Formatage des points pour le graphique
  const chartData = (mixHistory || []).map((pt) => {
    const d = new Date(pt.date_heure);
    return {
      ...pt,
      formattedTime: `${d.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} ${d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`,
    };
  });

  const borderFlows = [
    { country: 'Royaume-Uni', code: 'UK', mw: echanges.angleterre_mw },
    { country: 'Espagne', code: 'ES', mw: echanges.espagne_mw },
    { country: 'Italie', code: 'IT', mw: echanges.italie_mw },
    { country: 'Suisse', code: 'CH', mw: echanges.suisse_mw },
    { country: 'Allemagne & Belgique', code: 'DE-BE', mw: echanges.allemagne_belgique_mw },
  ];

  return (
    <div className="tab-content-container fade-in">
      {/* 1. GRILLE DE KPIS MAJEURS */}
      <section className="kpi-grid">
        {/* Consommation */}
        <div className="kpi-card glass-panel highlight-gold">
          <div className="kpi-header">
            <span className="kpi-title">Consommation Nationale</span>
            <div className="kpi-icon-badge gold">
              <Zap size={18} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{latestMetrics.consommation_mw.toLocaleString('fr-FR')}</span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-subtext">
            <span>Prévision J : {latestMetrics.prevision_j_mw ? `${latestMetrics.prevision_j_mw.toLocaleString('fr-FR')} MW` : 'N/D'}</span>
          </div>
        </div>

        {/* Production Totale */}
        <div className="kpi-card glass-panel">
          <div className="kpi-header">
            <span className="kpi-title">Production Réalisée</span>
            <div className="kpi-icon-badge blue">
              <Layers size={18} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{latestMetrics.production_totale_mw.toLocaleString('fr-FR')}</span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-subtext">
            <span>Nucléaire + EnR + Thermique</span>
          </div>
        </div>

        {/* Part Décarbonée */}
        <div className="kpi-card glass-panel highlight-green">
          <div className="kpi-header">
            <span className="kpi-title">Électricité Décarbonée</span>
            <div className="kpi-icon-badge green">
              <Sparkles size={18} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-main-number text-green">{latestMetrics.part_decarbonee_pct}</span>
            <span className="kpi-unit">%</span>
          </div>
          <div className="kpi-subtext">
            <span>Nucléaire ({((filieres.nucleaire_mw / totalProd) * 100).toFixed(1)}%) + EnR ({latestMetrics.part_renouvelable_pct}%)</span>
          </div>
        </div>

        {/* Intensité Carbone */}
        <div className="kpi-card glass-panel">
          <div className="kpi-header">
            <span className="kpi-title">Intensité Carbone</span>
            <div className="kpi-icon-badge pink">
              <TrendingDown size={18} />
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{latestMetrics.taux_co2_g_kwh}</span>
            <span className="kpi-unit">gCO2/kWh</span>
          </div>
          <div className="kpi-subtext">
            <span>Standard européen moyen : ~250 g</span>
          </div>
        </div>

        {/* Solde Échanges */}
        <div className="kpi-card glass-panel">
          <div className="kpi-header">
            <span className="kpi-title">Solde Frontalier</span>
            <div className={`kpi-icon-badge ${echanges.ech_physiques_mw < 0 ? 'gold' : 'blue'}`}>
              {echanges.ech_physiques_mw < 0 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
            </div>
          </div>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{Math.abs(echanges.ech_physiques_mw).toLocaleString('fr-FR')}</span>
            <span className="kpi-unit">MW</span>
          </div>
          <div className="kpi-subtext">
            <span className="badge-pill">{echanges.statut_solde}</span>
          </div>
        </div>
      </section>

      {/* 2. GRAPHIQUE INTERACTIF DU MIX 30 MINUTES */}
      <section className="chart-section glass-panel">
        <div className="section-header-row">
          <div>
            <h3 className="section-heading">Dynamique Temporelle du Mix Électrique (30 min)</h3>
            <p className="section-subheading">
              Évolution continue de la consommation et de la puissance fournie par filière technologique
            </p>
          </div>

          {/* Sélecteur de Plage Temporelle */}
          <div className="range-selector">
            <button 
              className={`range-btn ${historyRange === 48 ? 'active' : ''}`}
              onClick={() => setHistoryRange(48)}
            >
              24 Heures
            </button>
            <button 
              className={`range-btn ${historyRange === 96 ? 'active' : ''}`}
              onClick={() => setHistoryRange(96)}
            >
              48 Heures
            </button>
            <button 
              className={`range-btn ${historyRange === 336 ? 'active' : ''}`}
              onClick={() => setHistoryRange(336)}
            >
              7 Jours
            </button>
          </div>
        </div>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={380}>
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="gradNuc" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#38BDF8" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="gradHydro" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284C7" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#0284C7" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="gradWind" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60A5FA" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#60A5FA" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="gradSolar" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FBBF24" stopOpacity={0.9}/>
                  <stop offset="95%" stopColor="#FBBF24" stopOpacity={0.2}/>
                </linearGradient>
                <linearGradient id="gradBio" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#34D399" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#34D399" stopOpacity={0.1}/>
                </linearGradient>
                <linearGradient id="gradGas" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FB923C" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#FB923C" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis 
                dataKey="formattedTime" 
                stroke="#64748B" 
                fontSize={12} 
                tickLine={false} 
              />
              <YAxis 
                stroke="#64748B" 
                fontSize={12} 
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k MW`}
                tickLine={false}
              />
              <Tooltip 
                contentStyle={{
                  backgroundColor: '#0A172C',
                  borderColor: '#F5B82E',
                  borderRadius: '10px',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                  color: '#FFFFFF'
                }}
                formatter={(val, name) => [`${val.toLocaleString('fr-FR')} MW`, name]}
              />
              <Legend wrapperStyle={{ paddingTop: 10 }} />
              
              {/* Filières empilées */}
              <Area type="monotone" dataKey="nucleaire_mw" name="Nucléaire" stackId="1" stroke="#38BDF8" fill="url(#gradNuc)" />
              <Area type="monotone" dataKey="hydraulique_mw" name="Hydraulique" stackId="1" stroke="#0284C7" fill="url(#gradHydro)" />
              <Area type="monotone" dataKey="eolien_mw" name="Éolien" stackId="1" stroke="#60A5FA" fill="url(#gradWind)" />
              <Area type="monotone" dataKey="solaire_mw" name="Solaire" stackId="1" stroke="#FBBF24" fill="url(#gradSolar)" />
              <Area type="monotone" dataKey="bioenergies_mw" name="Bioénergies" stackId="1" stroke="#34D399" fill="url(#gradBio)" />
              <Area type="monotone" dataKey="gaz_mw" name="Gaz Thermique" stackId="1" stroke="#FB923C" fill="url(#gradGas)" />
              
              {/* Consommation appelée (Courbe d'alignement) */}
              <Line type="monotone" dataKey="consommation_mw" name="Consommation Réseau" stroke="#FFFFFF" strokeWidth={2.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* 3. DÉCOMPOSITION INSTANTANÉE PAR FILIÈRE & FLUX TRANSFRONTALIERS */}
      <div className="details-two-columns">
        {/* Filières de Production */}
        <div className="column-card glass-panel">
          <h4 className="card-section-title">Répartition Instantanée de la Production</h4>
          <p className="card-section-subtitle">Dernier relevé à {new Date(latestMetrics.date_heure).toLocaleTimeString('fr-FR')}</p>

          <div className="filieres-list">
            {filieresList.map((f) => {
              const Icon = f.icon;
              const pct = ((f.val / totalProd) * 100).toFixed(1);
              return (
                <div key={f.key} className="filiere-item">
                  <div className="filiere-info-left">
                    <div className="filiere-icon" style={{ backgroundColor: `${f.color}22`, color: f.color }}>
                      <Icon size={16} />
                    </div>
                    <div>
                      <span className="filiere-name">{f.name}</span>
                      <span className="filiere-category">{f.cat}</span>
                    </div>
                  </div>
                  <div className="filiere-info-right">
                    <span className="filiere-power">{f.val.toLocaleString('fr-FR')} MW</span>
                    <span className="filiere-percent" style={{ color: f.color }}>{pct}%</span>
                  </div>
                  <div className="filiere-bar-bg">
                    <div className="filiere-bar-fill" style={{ width: `${Math.min(pct * 1.5, 100)}%`, backgroundColor: f.color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Échanges Commerciaux aux Frontières */}
        <div className="column-card glass-panel">
          <div className="borders-header-row">
            <div>
              <h4 className="card-section-title">Interconnexions Européennes</h4>
              <p className="card-section-subtitle">Flux commerciaux bilatéraux en temps réel</p>
            </div>
            <div className="overall-flow-badge">
              <span>Solde : {echanges.ech_physiques_mw.toLocaleString('fr-FR')} MW</span>
            </div>
          </div>

          <div className="borders-list">
            {borderFlows.map((b) => {
              const val = b.mw || 0;
              const isExport = val < 0;
              return (
                <div key={b.code} className="border-item">
                  <div className="border-country-box">
                    <span className="country-code-badge">{b.code}</span>
                    <span className="country-name">{b.country}</span>
                  </div>
                  <div className="border-flow-info">
                    <span className="border-flow-power">{Math.abs(val).toLocaleString('fr-FR')} MW</span>
                    <span className={`flow-tag ${isExport ? 'export' : 'import'}`}>
                      {isExport ? 'Exportation →' : '← Importation'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="border-footer-note">
            <p>
              * Conformément aux conventions RTE éCO2mix, un solde négatif indique un flux sortant (la France exporte son surplus décarboné).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
