from dashboard.api.main import app

def test_routes_exist():
    paths = {route.path for route in app.routes}
    assert '/api/health' in paths
    assert '/api/portfolio/summary' in paths
    assert '/api/portfolio/valuation' in paths
    assert '/api/trades/positions' in paths
    assert '/api/operations/scanner/runs' in paths
    assert '/api/operations/manager/runs' in paths

def test_health():
    from dashboard.api.main import health
    assert health()['status'] == 'ok'
