"""Tests d'intégration de l'API REST FastAPI de l'Observatoire Énergétique."""

import pytest
from fastapi.testclient import TestClient

from src.energy_observatory.api.main import app
from src.energy_observatory.storage.db import check_connection

client = TestClient(app)
db_available = check_connection()


def test_api_root():
    """Vérifie le point d'entrée racine / et ses métadonnées."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Observatoire des Données Énergétiques de la France"
    assert data["version"] == "1.0.0"
    assert "endpoints_v1" in data
    assert "documentation" in data


def test_openapi_spec():
    """Vérifie que la spécification OpenAPI 3 est générée sans erreur."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "paths" in spec
    assert "/api/v1/health" in spec["paths"]
    assert "/api/v1/metrics/latest" in spec["paths"]
    assert "/api/v1/mix/history" in spec["paths"]
    assert "/api/v1/capacities/regional" in spec["paths"]


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_health():
    """Vérifie les endpoints /health et /api/v1/health."""
    for path in ["/health", "/api/v1/health"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database_connected"] is True
        assert data["tables_counts"]["gold.fact_electricite_national_30min"] > 0
        assert data["tables_counts"]["gold.fact_registre_installations"] > 0
        assert data["tables_counts"]["gold.fact_acces_electricite_annuel"] == 66


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_metrics_latest():
    """Vérifie le endpoint /api/v1/metrics/latest."""
    response = client.get("/api/v1/metrics/latest")
    assert response.status_code == 200
    data = response.json()

    assert "date_heure" in data
    assert data["consommation_mw"] > 0
    assert data["production_totale_mw"] > 0
    assert 0 <= data["part_renouvelable_pct"] <= 100
    assert 0 <= data["part_decarbonee_pct"] <= 100
    assert "filieres" in data
    assert "nucleaire_mw" in data["filieres"]
    assert "echanges" in data
    assert data["echanges"]["statut_solde"] in ["Exportateur net", "Importateur net", "Équilibré"]


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_mix_history():
    """Vérifie le endpoint /api/v1/mix/history avec limitation."""
    response = client.get("/api/v1/mix/history?limit=10")
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 10
    assert len(data["points"]) == 10

    # Vérification de l'ordre chronologique croissant
    dates = [p["date_heure"] for p in data["points"]]
    assert dates == sorted(dates)

    first_pt = data["points"][0]
    assert first_pt["consommation_mw"] > 0
    assert first_pt["production_totale_mw"] > 0


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_mix_monthly():
    """Vérifie le endpoint /api/v1/mix/monthly."""
    response = client.get("/api/v1/mix/monthly?limit=12")
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] > 0
    assert len(data["points"]) <= 12
    first_month = data["points"][0]
    assert first_month["annee"] >= 2012
    assert 1 <= first_month["mois"] <= 12
    assert first_month["conso_moyenne_mw"] > 0
    assert first_month["part_decarbonee_pct"] > 50.0


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_regional_capacities():
    """Vérifie le endpoint /api/v1/capacities/regional."""
    response = client.get("/api/v1/capacities/regional?limit=20")
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] > 0
    first_item = data["items"][0]
    assert "region" in first_item
    assert "libelle_filiere" in first_item
    assert first_item["puissance_totale_mw"] > 0
    assert first_item["nb_installations"] > 0


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_capacities_summary():
    """Vérifie le endpoint /api/v1/capacities/summary."""
    response = client.get("/api/v1/capacities/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["total_installations"] >= 125000
    assert data["total_puissance_mw"] > 100000.0  # Plus de 100 GW installés
    assert len(data["categories"]) >= 3


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_international_access():
    """Vérifie le endpoint /api/v1/international/access."""
    response = client.get("/api/v1/international/access")
    assert response.status_code == 200
    data = response.json()

    assert data["total_records"] == 66
    annees = [p["annee"] for p in data["points"]]
    assert min(annees) == 1960
    assert max(annees) == 2025


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_mix_history_with_date_filters():
    """Vérifie le filtrage par plage de dates sur /api/v1/mix/history."""
    # Test avec start_date et end_date
    response = client.get("/api/v1/mix/history?start_date=2026-01-01T00:00:00&end_date=2026-01-01T02:00:00&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] > 0
    assert len(data["points"]) <= 10

    # Test avec start_date uniquement
    response2 = client.get("/api/v1/mix/history?start_date=2026-01-01T00:00:00&limit=5")
    assert response2.status_code == 200
    assert response2.json()["total_records"] > 0


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_mix_monthly_filtered():
    """Vérifie le filtrage par année sur /api/v1/mix/monthly."""
    response = client.get("/api/v1/mix/monthly?annee=2025")
    assert response.status_code == 200
    data = response.json()
    for pt in data["points"]:
        assert pt["annee"] == 2025


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_regional_capacities_filtered():
    """Vérifie le filtrage par région et par filière sur /api/v1/capacities/regional."""
    response = client.get("/api/v1/capacities/regional?code_region=84&code_filiere=solaire")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["code_region"] == "84"
        assert item["code_filiere"] == "solaire"


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_international_access_filtered():
    """Vérifie le filtrage par plage d'années sur /api/v1/international/access."""
    response = client.get("/api/v1/international/access?annee_min=2000&annee_max=2020")
    assert response.status_code == 200
    data = response.json()
    for pt in data["points"]:
        assert 2000 <= pt["annee"] <= 2020


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_quality_report():
    """Vérifie le endpoint /api/v1/quality/report avec rapport existant."""
    response = client.get("/api/v1/quality/report")
    assert response.status_code == 200
    data = response.json()
    assert data["global_score_pct"] == 100.0
    assert data["total_rules"] == 10
    assert data["passed_rules"] == 10
    assert data["failed_rules"] == 0
    assert data["status"] == "PASS"
    assert len(data["rules"]) == 10


@pytest.mark.skipif(not db_available, reason="PostgreSQL non accessible")
def test_api_quality_report_forced_refresh():
    """Vérifie l'exécution forcée du validateur via refresh=true."""
    response = client.get("/api/v1/quality/report?refresh=true")
    assert response.status_code == 200
    data = response.json()
    assert data["global_score_pct"] == 100.0
    assert data["total_rules"] == 10


