import React, { useState } from 'react';
import { 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts';
import { Calendar, TrendingUp, Award, Filter } from 'lucide-react';

export default function MonthlyHistoryTab({ monthlyData, isLoading }) {
  const [selectedYear, setSelectedYear] = useState('ALL');

  if (!monthlyData || monthlyData.length === 0) {
    return (
      <div className="tab-loading-state glass-panel">
        <Calendar className="spin-animation icon-gold" size={32} />
        <p>Chargement des agrégations mensuelles (2012 - 2026)...</p>
      </div>
    );
  }

  // Filtrage des années
  const years = ['ALL', ...Array.from(new Set(monthlyData.map(m => m.annee))).sort((a, b) => b - a)];
  
  const filteredData = selectedYear === 'ALL' 
    ? [...monthlyData].reverse() 
    : [...monthlyData].filter(m => m.annee === parseInt(selectedYear)).reverse();

  // Statistiques clés calculées sur l'échantillon
  const maxPeak = Math.max(...filteredData.map(d => d.pointe_consommation_mw));
  const avgDecarbonized = (filteredData.reduce((acc, d) => acc + d.part_decarbonee_pct, 0) / (filteredData.length || 1)).toFixed(1);
  const avgRenewable = (filteredData.reduce((acc, d) => acc + d.part_renouvelable_pct, 0) / (filteredData.length || 1)).toFixed(1);
  const avgCo2 = (filteredData.reduce((acc, d) => acc + d.intensite_co2_moyenne_g_kwh, 0) / (filteredData.length || 1)).toFixed(1);

  return (
    <div className="tab-content-container fade-in">
      {/* Barre de contrôle et Filtres */}
      <div className="control-bar glass-panel">
        <div className="control-title">
          <Calendar size={18} className="icon-gold" />
          <span>Historique Consolidé du Mix Énergétique Français (Vue Gold)</span>
        </div>
        <div className="year-filter-wrapper">
          <Filter size={15} className="text-secondary" />
          <span>Filtrer par année :</span>
          <select 
            className="styled-select"
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
          >
            {years.map(y => (
              <option key={y} value={y}>{y === 'ALL' ? 'Toutes les années (2012-2026)' : y}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Mini KPIs d'Historique */}
      <div className="kpi-grid">
        <div className="kpi-card glass-panel">
          <span className="kpi-title">Pointe Maximale Observée</span>
          <div className="kpi-value-row">
            <span className="kpi-main-number text-gold">{maxPeak.toLocaleString('fr-FR')}</span>
            <span className="kpi-unit">MW</span>
          </div>
          <span className="kpi-subtext">Record de puissance appelée</span>
        </div>
        <div className="kpi-card glass-panel">
          <span className="kpi-title">Taux Décarboné Moyen</span>
          <div className="kpi-value-row">
            <span className="kpi-main-number text-green">{avgDecarbonized}</span>
            <span className="kpi-unit">%</span>
          </div>
          <span className="kpi-subtext">Nucléaire + Renouvelable</span>
        </div>
        <div className="kpi-card glass-panel">
          <span className="kpi-title">Taux Renouvelable Moyen</span>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{avgRenewable}</span>
            <span className="kpi-unit">%</span>
          </div>
          <span className="kpi-subtext">Éolien, solaire, hydro, biomasse</span>
        </div>
        <div className="kpi-card glass-panel">
          <span className="kpi-title">Émissions CO2 Moyennes</span>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{avgCo2}</span>
            <span className="kpi-unit">g/kWh</span>
          </div>
          <span className="kpi-subtext">Empreinte carbone du mix</span>
        </div>
      </div>

      {/* Graphique 1 : Consommation Moyenne vs Pointe de Consommation */}
      <section className="chart-section glass-panel">
        <h3 className="section-heading">Consommation Moyenne et Pointes Mensuelles (MW)</h3>
        <p className="section-subheading">Mise en évidence de la saisonnalité hivernale et de la thermo-sensibilité française</p>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={filteredData} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis 
                dataKey="mois_nom" 
                stroke="#64748B" 
                fontSize={11}
                tickFormatter={(v, i) => `${filteredData[i]?.mois_nom?.slice(0, 3)} ${filteredData[i]?.annee}`}
              />
              <YAxis 
                stroke="#64748B" 
                fontSize={11}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k MW`}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0A172C', borderColor: '#F5B82E', borderRadius: '10px' }}
                formatter={(val, name) => [`${val.toLocaleString('fr-FR')} MW`, name]}
                labelFormatter={(label, payload) => payload?.[0] ? `${payload[0].payload.mois_nom} ${payload[0].payload.annee}` : label}
              />
              <Legend />
              <Bar dataKey="conso_moyenne_mw" name="Consommation Moyenne" fill="#2563EB" radius={[4, 4, 0, 0]} />
              <Bar dataKey="pointe_consommation_mw" name="Pointe de Puissance" fill="#F5B82E" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Graphique 2 : Part Décarbonée et Intensité Carbone */}
      <section className="chart-section glass-panel">
        <h3 className="section-heading">Évolution de la Part Décarbonée et Intensité CO2</h3>
        <p className="section-subheading">Trajectoire de décarbonation du système électrique</p>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={filteredData} margin={{ top: 10, right: 30, left: 10, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis 
                dataKey="mois_nom" 
                stroke="#64748B" 
                fontSize={11}
                tickFormatter={(v, i) => `${filteredData[i]?.mois_nom?.slice(0, 3)} ${filteredData[i]?.annee}`}
              />
              <YAxis yAxisId="left" stroke="#10B981" fontSize={11} unit="%" domain={[60, 100]} />
              <YAxis yAxisId="right" orientation="right" stroke="#EC4899" fontSize={11} unit="g" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0A172C', borderColor: '#F5B82E', borderRadius: '10px' }}
                labelFormatter={(label, payload) => payload?.[0] ? `${payload[0].payload.mois_nom} ${payload[0].payload.annee}` : label}
              />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="part_decarbonee_pct" name="Part Décarbonée (%)" stroke="#10B981" strokeWidth={2.5} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="intensite_co2_moyenne_g_kwh" name="Intensité CO2 (g/kWh)" stroke="#EC4899" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
