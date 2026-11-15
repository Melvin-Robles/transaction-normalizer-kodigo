"""Contrato de exportación. Requiere implementación futura de Codex."""
import json
from decimal import Decimal

from transaction_normalizer.exports import serialize_normalized_json, serialize_errors_json


def test_amount_json_es_numero_y_esquema_exacto():
    normalized = [{
        'id': 'tx_001', 'amount': Decimal('100.50'), 'currency': 'USD',
        'timestamp': '2025-03-10T14:22:00Z', 'status': 'SUCCESS', 'source': 'A'
    }]
    data = json.loads(serialize_normalized_json(normalized))
    assert isinstance(data,list) and len(data)==1
    assert set(data[0])=={'id','amount','currency','timestamp','status','source'}
    assert isinstance(data[0]['amount'], (int,float))
    assert not isinstance(data[0]['amount'],bool)
    assert Decimal(str(data[0]['amount']))==Decimal('100.50')


def test_json_de_invalidos_no_arrastra_carga_original():
    errors = [{'index': 0, 'source': 'A', 'error_code': 'INVALID_AMOUNT', 'message': 'Monto inválido'}]
    data = json.loads(serialize_errors_json(errors))
    assert data==errors


def test_exportacion_vacia_es_arreglo_vacio():
    assert json.loads(serialize_normalized_json([]))==[]
    assert json.loads(serialize_errors_json([]))==[]
