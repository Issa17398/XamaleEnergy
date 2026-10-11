import React, { useState } from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { MapPin, Search, Server, Cpu, CheckCircle } from 'lucide-react';

export default function CapacitiesTab({ 
  regionalData, 
  summaryData, 
  isLoading 
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFiliere, setSelectedFiliere] = useState('ALL');

  if (!summaryData || !regionalData) {
    return (
      <div className="tab-loading-state glass-panel">
        <MapPin className="spin-animation icon-gold" size={32} />
        <p>Chargement du Registre National des Installations (Enedis 2025)...</p>
      </div>
    );
  }

  // Filtrage du tableau
  const filieresList = ['ALL', ...Array.from(new Set(regionalData.map(r => r.libelle_filiere)))];

  const filteredItems = regionalData.filter(item => {
    const matchesSearch = item.region.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          item.libelle_filiere.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFiliere = selectedFiliere === 'ALL' || item.libelle_filiere === selectedFiliere;
    return matchesSearch && matchesFiliere;
  });

  // Top 10 des régions en puissance totale
  const regionAggregated = {};
  regionalData.forEach(r => {
    if (!regionAggregated[r.region]) regionAggregated[r.region] = 0;
    regionAggregated[r.region] += r.puissance_totale_mw;
  });

  const chartData = Object.entries(regionAggregated)
    .map(([region, total]) => ({ region, puissance_mw: Math.round(total) }))
    .sort((a, b) => b.puissance_mw - a.puissance_mw)
    .slice(0, 10);

  return (
    <div className="tab-content-container fade-in">
      {/* Synthèse Nationale */}
      <section className="kpi-grid">
        <div className="kpi-card glass-panel highlight-gold">
          <span className="kpi-title">Parc Installé National</span>
          <div className="kpi-value-row">
            <span className="kpi-main-number">{summaryData.total_puissance_mw?.toLocaleString('fr-FR')}</span>
            <span className="kpi-unit">MW</span>
          </div>
          <span className="kpi-subtext">{summaryData.total_installations?.toLocaleString('fr-FR')} installations actives</span>
        </div>

        {summaryData.categories?.map(cat => (
          <div key={cat.categorie_energie} className="kpi-card glass-panel">
            <span className="kpi-title">{cat.categorie_energie}</span>
            <div className="kpi-value-row">
              <span className="kpi-main-number">{cat.puissance_totale_mw.toLocaleString('fr-FR')}</span>
              <span className="kpi-unit">MW</span>
            </div>
            <span className="kpi-subtext">{cat.part_pct}% du parc • {cat.nb_installations.toLocaleString('fr-FR')} sites</span>
          </div>
        ))}
      </section>

      {/* Graphique des Top Régions Productrices */}
      <section className="chart-section glass-panel">
        <h3 className="section-heading">Top 10 Régions par Puissance Raccordée (MW)</h3>
        <p className="section-subheading">Capacités de production cumulées selon le Registre National Enedis au 31/12/2025</p>

        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 10, right: 30, left: 140, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis type="number" stroke="#64748B" fontSize={11} tickFormatter={(v) => `${(v/1000).toFixed(0)}k MW`} />
              <YAxis type="category" dataKey="region" stroke="#CBD5E1" fontSize={11} width={130} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#0A172C', borderColor: '#F5B82E', borderRadius: '10px' }}
                formatter={(val) => [`${val.toLocaleString('fr-FR')} MW`, 'Puissance raccordée']}
              />
              <Bar dataKey="puissance_mw" fill="#F5B82E" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      {/* Table et Filtres Détaillés */}
      <section className="column-card glass-panel">
        <div className="table-filter-header">
          <div>
            <h4 className="card-section-title">Inventaire Régional des Capacités Raccordées</h4>
            <p className="card-section-subtitle">Détail par région administrative et technologie ({filteredItems.length} lignes)</p>
          </div>

          <div className="filters-row">
            {/* Champ de recherche */}
            <div className="search-box">
              <Search size={15} className="text-secondary" />
              <input 
                type="text" 
                placeholder="Rechercher une région..." 
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="styled-input"
              />
            </div>

            {/* Sélecteur de filière */}
            <select 
              className="styled-select"
              value={selectedFiliere}
              onChange={(e) => setSelectedFiliere(e.target.value)}
            >
              {filieresList.map(f => (
                <option key={f} value={f}>{f === 'ALL' ? 'Toutes les filières' : f}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="table-responsive-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th>Région</th>
                <th>Filière de Production</th>
                <th>Catégorie</th>
                <th className="text-right">Nb Installations</th>
                <th className="text-right">Puissance (MW)</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.slice(0, 50).map((row, idx) => (
                <tr key={`${row.region}-${row.code_filiere}-${idx}`}>
                  <td>
                    <span className="region-name-cell">{row.region}</span>
                    <span className="region-code-sub">({row.code_region})</span>
                  </td>
                  <td>{row.libelle_filiere}</td>
                  <td>
                    <span className={`category-tag ${row.categorie_energie?.toLowerCase()}`}>
                      {row.categorie_energie}
                    </span>
                  </td>
                  <td className="text-right font-mono">{row.nb_installations.toLocaleString('fr-FR')}</td>
                  <td className="text-right font-mono text-gold font-bold">{row.puissance_totale_mw.toLocaleString('fr-FR')} MW</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
