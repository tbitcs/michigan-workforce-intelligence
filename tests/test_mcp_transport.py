"""Real MCP SDK HTTP contract tests, using isolated synthetic evidence."""
from datetime import UTC, datetime

import pytest
from starlette.testclient import TestClient

from mijobs import mcp_server
from mijobs.db import initialize_database, make_engine, session_factory
from mijobs.domain import ClaimKind
from mijobs.repository import EvidenceRepository


@pytest.fixture
def mcp_client(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'transport.db'}"
    monkeypatch.setenv('MIJOBS_DATABASE_URL', url)
    monkeypatch.setenv('MIJOBS_MCP_WRITE_ENABLED', 'false')
    engine = make_engine(url)
    initialize_database(engine)
    with session_factory(engine)() as session:
        repo = EvidenceRepository(session)
        artifact = repo.add_source_artifact(
            source_id='us_bls_api', source_locator='https://api.bls.gov/test',
            retrieved_at=datetime.now(UTC), content_sha256='a' * 64,
            media_type='application/json', byte_size=2, local_path='synthetic-test',
        )
        claim = repo.add_claim(claim_key='synthetic', text='Synthetic test claim', kind=ClaimKind.HYPOTHESIS)
        ids = {'artifact_id': artifact.id, 'claim_id': claim.id}
        session.commit()
    server = mcp_server.build_server()
    app = server.streamable_http_app(json_response=True, stateless_http=True)
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        yield client, ids
    engine.dispose()


def metric(value):
    return dict(value=value, unit='people_per_year', geography_code='26', period_basis='annual',
                taxonomy_system='SOC', taxonomy_version='2024', taxonomy_code='49-9041')


ASSUMPTIONS = dict(annual_training_seats='100', cost_per_seat='5000', completion_rate='0.8',
                   placement_rate='0.75', michigan_retention_rate='0.9', counterfactual_entry_share='0.25')
CASES = [
    ('sources_list', {}, False), ('observations_search', {}, False),
    ('claims_search', {}, False), ('mappings_search', {}, False),
    ('artifacts_get', {'artifact_id': '$artifact_id'}, False),
    ('claims_get', {'claim_id': '$claim_id'}, False),
    ('claims_trace', {'claim_id': '$claim_id'}, False),
    ('ledger_verify', {}, False), ('ledger_audit', {}, False),
    ('report_context', {'claim_ids': ['$claim_id']}, False),
    ('gap_market_tightness', {'online_job_ads': '100', 'available_people': '50'}, False),
    ('gap_training_pipeline', {'payload': {'annual_openings': metric('100'), 'completions': metric('60')}}, False),
    ('policy_training_scenario', {'payload': {'baseline_gap_workers': '100', 'low': ASSUMPTIONS,
                                             'base': ASSUMPTIONS, 'high': ASSUMPTIONS}}, False),
    ('claims_challenge', {'claim_id': '$claim_id', 'rationale': 'Test writes disabled'}, True),
    ('observations_search', {'limit': 0}, True), ('claims_search', {'limit': 501}, True),
    ('mappings_search', {'limit': -1}, True),
    ('gap_market_tightness', {'online_job_ads': '-1', 'available_people': '50'}, True),
    ('gap_training_pipeline', {'payload': {}}, True),
    ('policy_training_scenario', {'payload': {}}, True),
]


@pytest.mark.parametrize('name,arguments,error', CASES)
def test_real_http_tool_contract(mcp_client, name, arguments, error):
    client, ids = mcp_client
    arguments = {key: ids[value[1:]] if isinstance(value, str) and value.startswith('$')
                 else [ids['claim_id']] if key == 'claim_ids' else value
                 for key, value in arguments.items()}
    response = client.post('/mcp', headers={'Accept': 'application/json, text/event-stream'},
                           json={'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                                 'params': {'name': name, 'arguments': arguments}})
    assert response.status_code == 200
    result = response.json()['result']
    assert result.get('isError', False) is error
    if not error:
        assert result['structuredContent']
        if name in ('ledger_verify', 'ledger_audit'):
            assert result['structuredContent']['valid'] is True
        if name == 'gap_training_pipeline':
            assert result['structuredContent']['gap'] == '40'
        if name == 'claims_get':
            assert result['structuredContent']['text'] == 'Synthetic test claim'
