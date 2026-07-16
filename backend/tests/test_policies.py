import pytest

from app.policies import safe_invoice_filter, safe_order_read_filter, safe_order_update


def test_order_read_rebuilds_filter_with_owner():
    malicious = {"order_id": "PED-1001", "owner_customer_key": "bruno", "$where": "true"}
    assert safe_order_read_filter(malicious, "ana") == {
        "order_id": "PED-1001",
        "owner_customer_key": "ana",
    }


def test_order_write_strips_upsert_and_unapproved_fields():
    query, update = safe_order_update(
        {"order_id": "PED-1001", "status": "reembolsado", "upsert": True, "$inc": {"amount": 99}},
        "ana",
    )
    assert query == {"order_id": "PED-1001", "owner_customer_key": "ana"}
    assert update == {"$set": {"status": "reembolsado"}}


@pytest.mark.parametrize("status", ["cancelado_admin", "fraude", "", "ENTREGUE_AGORA"])
def test_order_write_rejects_unknown_status(status):
    with pytest.raises(ValueError):
        safe_order_update({"order_id": "PED-1001", "status": status}, "ana")


def test_invoice_filter_never_accepts_foreign_owner():
    assert safe_invoice_filter({"invoice_id": "FAT-1001", "owner_customer_key": "bruno"}, "ana") == {
        "invoice_id": "FAT-1001",
        "owner_customer_key": "ana",
    }

