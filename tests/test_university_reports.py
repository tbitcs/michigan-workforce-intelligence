from __future__ import annotations

import io
import json
import zipfile
from datetime import UTC, datetime

import httpx
import pytest
from openpyxl import Workbook
from sqlalchemy import select

from mijobs.artifact_store import ArtifactStore
from mijobs.ingestion import Ingestor
from mijobs.ledger import verify_ledger
from mijobs.models import Claim, Observation
from mijobs.sources.base import FetchedArtifact
from mijobs.sources.institutions import PARTNER_UNITIDS
from mijobs.sources.ipeds import IPEDSConnector
from mijobs.university_reports import harvest_universities, university_report


def completion_zip(unitids=PARTNER_UNITIDS):
    content = 'UNITID,CIPCODE,MAJORNUM,AWLEVEL,CTOTALT,XCTOTALT\n'
    for unitid in unitids:
        for cip,major,count in [('11.0701','1','20'),('11.0701','2','5'),('11','1','20'),('99.0000','1','20')]:
            content += f'{unitid},{cip},{major},5,{count},R\n'
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('c2024_a.csv', content)
    return stream.getvalue()


def crosswalk_xlsx():
    book = Workbook()
    book.active.title = 'CIP-SOC'
    book.active.append(['CIP2020Code','CIP2020Title','SOC2018Code','SOC2018Title'])
    book.active.append(['11.0701','Computer Science','15-1252','Software Developers'])
    book.active.append(['99.9999','NO MATCH','15-9999','Other'])
    stream=io.BytesIO()
    book.save(stream)
    return stream.getvalue()


def mock_client(monkeypatch, *, missing=False, bad_coverage=False):
    def respond(request):
        if request.url.path.endswith('.json'):
            body=json.dumps({"results":[{"id":int(u),"2020.earnings.10_yrs_after_entry.median":50000,
                  "2024.completion.completion_rate_4yr_150nt":0.5} for u in PARTNER_UNITIDS]}).encode()
        elif request.url.path.endswith('.zip'):
            body=completion_zip(('170675',)) if missing else completion_zip()
        elif request.url.path.endswith('.xlsx'):
            body=crosswalk_xlsx()
        else:
            body=b'wrong\nvalue\n' if bad_coverage else b'institution,label\n00232500,University of Michigan\n'
        return httpx.Response(200,content=body)
    client=httpx.Client(transport=httpx.MockTransport(respond))
    monkeypatch.setattr('mijobs.university_reports.governed_client',lambda **kwargs:client)


def test_harvest_report_lineage_and_no_double_count(db_session,tmp_path,monkeypatch):
    mock_client(monkeypatch)
    result=harvest_universities(db_session,ArtifactStore(tmp_path))
    assert result['observations']==16
    assert result['mappings']==1
    head=verify_ledger(db_session).head_hash
    report=university_report(db_session)
    assert len(report['artifacts'])==4
    assert all(i['total_first_major_awards']==20 for i in report['institutions'])
    assert all(len(i['programs'])==1 for i in report['institutions'])
    assert report['institutions'][0]['programs'][0]['related_soc_codes']==['15-1252']
    assert report['pseo_coverage'][0]['label']=='University of Michigan'
    assert verify_ledger(db_session).head_hash==head
    rows=list(db_session.scalars(select(Observation)))
    assert len({r.observation_key for r in rows})==24
    assert all(r.version==1 for r in rows)


@pytest.mark.parametrize('option',[{'missing':True},{'bad_coverage':True}])
def test_harvest_refuses_incomplete_or_invalid_source(db_session,tmp_path,monkeypatch,option):
    mock_client(monkeypatch,**option)
    with pytest.raises(ValueError):
        harvest_universities(db_session,ArtifactStore(tmp_path))
    db_session.rollback()
    assert not list(db_session.scalars(select(Observation)))


def test_empty_report_and_unledgered_refusal(db_session):
    report=university_report(db_session)
    assert all(i['status']=='insufficient_data' for i in report['institutions'])
    db_session.add(Claim(id='unledgered',claim_key='unledgered',version=1,text='x',kind='reported',
                         status='unresolved',scope_json={},quality_json={},created_at=datetime.now(UTC)))
    db_session.flush()
    with pytest.raises(RuntimeError,match='unaudited'):
        university_report(db_session)


def test_missing_awards_are_not_zero(db_session,tmp_path):
    body=b'UNITID,CIPCODE,MAJORNUM,AWLEVEL,CTOTALT\n170675,11.0701,1,5,\n'
    artifact=FetchedArtifact(source_id='us_nces_ipeds',locator='https://nces.ed.gov/test.csv',
                             retrieved_at=datetime.now(UTC),content=body,media_type='text/csv',
                             metadata={'release_status':'provisional'})
    Ingestor(db_session,ArtifactStore(tmp_path)).ingest(artifact,normalizer=lambda a:IPEDSConnector().normalize_completions(a,collection_year=2024,cip_version='2020'))
    report=university_report(db_session)
    entry=next(i for i in report['institutions'] if i['unitid']=='170675')
    assert entry['status']=='insufficient_data'
    assert entry['total_first_major_awards'] is None


def test_scorecard_nulls_and_coverage_validation():
    from mijobs.university_reports import scorecard_observations
    data={"results":[{"id":int(u),"2020.earnings.10_yrs_after_entry.median":None,
          "2024.completion.completion_rate_4yr_150nt":0.5} for u in PARTNER_UNITIDS]}
    def artifact(body):
        return FetchedArtifact(source_id="us_ed_scorecard",locator="https://api.data.gov/test",
                               retrieved_at=datetime.now(UTC),content=json.dumps(body).encode(),media_type="application/json")
    rows=scorecard_observations(artifact(data))
    assert rows[0].numeric_value is None
    assert rows[0].period_start is None
    assert rows[1].metadata["data_year"]==2024
    with pytest.raises(ValueError,match="all configured"):
        scorecard_observations(artifact({"results":[]}))
