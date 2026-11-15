"""Pruebas de contrato (TDD): se ejecutarán DESPUÉS de que Codex cree la aplicación.

Este archivo define la API pública a respetar. No se asegura que haya tests
pasando antes de la implementación: todavía faltan src/ y requirements.txt.
"""
import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from transaction_normalizer.config import load_rules
from transaction_normalizer.ingest import parse_json_document
from transaction_normalizer.normalizer import normalize_records
from transaction_normalizer.metrics import calculate_metrics

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / 'config' / 'rules.json'
DATA = ROOT / 'data'


def A(id='a', amount='10.00', currency='USD', timestamp='2025-03-10 14:22:00', status='completed', **kwargs):
    return dict(id=id, amount=amount, currency=currency, timestamp=timestamp, status=status, **kwargs)


def B(transaction_id=1, total=1000, currency_code='usd', created_at='10/03/2025 14:22', state='OK', **kwargs):
    return dict(transaction_id=transaction_id, total=total, currency_code=currency_code, created_at=created_at, state=state, **kwargs)


def C(ref='c', amount='€10,00', date='2025-03-10T14:22:00Z', result='success', **kwargs):
    return dict(ref=ref, amount=amount, date=date, result=result, **kwargs)


@pytest.fixture
def rules():
    return load_rules(RULES)


def get_result(records, rules):
    return normalize_records(records, rules)


def expect_error(record, rules, code):
    result = get_result([record], rules)
    assert len(result.valid) == 0, f'Se aceptó erróneamente: {record}'
    assert len(result.invalid) == 1
    assert result.invalid[0]['error_code'] == code


def test_ejemplo_docente(rules):
    payload = (DATA / 'transacciones_ejemplo.json').read_bytes()
    records = parse_json_document(payload, rules)
    result = get_result(records, rules)
    assert len(result.valid) == 3
    assert result.invalid == []
    assert [row['id'] for row in result.valid] == ['tx_001', '204', 'A-77']
    assert [row['source'] for row in result.valid] == ['A', 'B', 'C']
    assert [row['amount'] for row in result.valid] == [Decimal('100.50'), Decimal('100.50'), Decimal('99.99')]
    assert {row['timestamp'] for row in result.valid} == {'2025-03-10T14:22:00Z'}
    assert {row['status'] for row in result.valid} == {'SUCCESS'}
    metrics = calculate_metrics(result.valid, result.invalid, total_processed=len(records))
    assert metrics['total_processed'] == 3
    assert metrics['valid_count'] == 3
    assert metrics['invalid_count'] == 0
    assert metrics['status_counts']['SUCCESS'] == 3
    assert metrics['all_valid_totals_by_currency']['USD'] == Decimal('201.00')
    assert metrics['all_valid_totals_by_currency']['EUR'] == Decimal('99.99')
    assert metrics['success_totals_by_currency']['USD'] == Decimal('201.00')


def test_vacio_y_contenedor(rules):
    empty = parse_json_document((DATA/'transacciones_vacias.json').read_bytes(), rules)
    assert empty == []
    assert len(get_result(empty, rules).valid) == 0
    wrapped = parse_json_document((DATA/'contenedor_transacciones.json').read_bytes(), rules)
    assert len(wrapped) == 1
    assert get_result(wrapped, rules).valid[0]['status'] == 'PENDING'


@pytest.mark.parametrize('file_name', ['entrada_malformada.json','raiz_invalida.json'])
def test_documento_invalido_error_controlado(rules,file_name):
    with pytest.raises(Exception):
        parse_json_document((DATA/file_name).read_bytes(), rules)


@pytest.mark.parametrize('record,code', [
    (None,'INVALID_RECORD_TYPE'),
    ('string','INVALID_RECORD_TYPE'),
    ([], 'INVALID_RECORD_TYPE'),
    ({'foo':'bar'},'UNKNOWN_SOURCE'),
    (dict(A('x'),transaction_id=1),'AMBIGUOUS_SOURCE'),
    ({'id':'x','amount':'10.00','timestamp':'2025-03-10 14:22:00','status':'completed'},'MISSING_FIELD'),
    (A('conflict',source='B'),'SOURCE_CONFLICT'),
    (A('x',amount=True),'INVALID_AMOUNT'),
    (A('x',amount='1,234.00'),'INVALID_AMOUNT'),
    (A('x',amount='1.999'),'INVALID_AMOUNT'),
    (A('x',amount='0.00'),'INVALID_AMOUNT'),
    (A('x',amount='-1.00'),'INVALID_AMOUNT'),
    (A('x',amount='1000000000.01'),'INVALID_AMOUNT'),
    (B(2,total=100.5),'INVALID_AMOUNT'),
    (C('x',amount='€1.234,56'),'INVALID_AMOUNT'),
    (C('x',amount='£99,99'),'INVALID_AMOUNT'),
    (C('x',currency='USD'),'CURRENCY_MISMATCH'),
    (A('x',currency='xyz'),'UNSUPPORTED_CURRENCY'),
    (B(2,currency_code='JPY'),'UNSUPPORTED_CURRENCY'),
    (B(2,state='completed'),'UNKNOWN_STATUS'),
    (A('x',status='unknown'),'UNKNOWN_STATUS'),
    (A('x',timestamp='2025-02-30 14:22:00'),'INVALID_TIMESTAMP'),
    (C('x',date='2025-03-10T14:22:00'),'INVALID_TIMESTAMP'),
    (A('   '),'INVALID_ID'),
    (A('x'*129),'INVALID_ID'),
    (B(True),'INVALID_ID'),
    (B(-1),'INVALID_ID'),
])
def test_validacion_precisa(rules, record, code):
    expect_error(record,rules,code)


def test_status_mayusculas_y_timezone(rules):
    result = get_result([A('s',status=' COMPLETED '), C('o',date='2025-03-10T16:22:00+02:00')],rules)
    assert len(result.valid)==2
    assert result.valid[0]['status']=='SUCCESS'
    assert result.valid[1]['timestamp']=='2025-03-10T14:22:00Z'


def test_multiples_estados_y_totales(rules):
    records=[A('ok', '10.00'), A('pending', '20.00',status='pending'), A('failed', '30.00',status='failed')]
    result=get_result(records,rules)
    m=calculate_metrics(result.valid,result.invalid,total_processed=len(records))
    assert m['status_counts']=={'SUCCESS':1,'FAILED':1,'PENDING':1}
    assert m['all_valid_totals_by_currency']['USD']==Decimal('60.00')
    assert m['success_totals_by_currency']['USD']==Decimal('10.00')


def test_duplicados_por_fuente(rules):
    result=get_result([A('shared'),A('shared'),C('shared')], rules)
    assert len(result.valid)==2
    assert result.invalid[0]['error_code']=='DUPLICATE_TRANSACTION'
    assert [r['source'] for r in result.valid]==['A','C']


def test_invalidos_no_reservan_id(rules):
    result=get_result([A('x',amount='1.999'),A('x',amount='10.00')],rules)
    assert len(result.valid)==1
    assert result.valid[0]['id']=='x'
    assert result.invalid[0]['error_code']=='INVALID_AMOUNT'


def test_configuracion_modificada_no_hardcode(rules):
    updated=copy.deepcopy(rules)
    updated['sources']['A']['status_map']['completed']='PENDING'
    result=get_result([A('updated')],updated)
    assert len(result.valid)==1
    assert result.valid[0]['status']=='PENDING'


def test_filas_adversariales_contrato(rules):
    rows=parse_json_document((DATA/'transacciones_casos_borde.json').read_bytes(),rules)
    expected=json.loads((ROOT/'tests'/'expectativas_casos_borde.json').read_text(encoding='utf-8'))
    assert len(rows)==len(expected)
    for spec in expected:
        row=rows[spec['index']]
        solo=get_result([row],rules)
        if spec['outcome']=='VALID':
            assert len(solo.valid)==1, f"Índice {spec['index']}: {solo.invalid}"
        elif spec['outcome']!='DUPLICATE_TRANSACTION':
            assert len(solo.invalid)==1, f"Índice {spec['index']}: {solo.valid}"
            assert solo.invalid[0]['error_code']==spec['outcome'], f"Índice {spec['index']}"
    result=get_result(rows,rules)
    assert len(rows)==len(result.valid)+len(result.invalid)
    assert {e['index'] for e in result.invalid} == {e['index'] for e in expected if e['outcome']!='VALID'}
    for err in result.invalid:
        assert err['error_code']==expected[err['index']]['outcome'], f"Índice {err['index']}"


def test_json_no_estandar_es_error_controlado(rules):
    for payload in (b'[NaN]',b'[Infinity]',b'\xff\xfe',b''):
        with pytest.raises(Exception):
            parse_json_document(payload,rules)


def test_limite_numero_registros(rules):
    payload=json.dumps([None]*10001).encode()
    with pytest.raises(Exception):
        parse_json_document(payload,rules)
