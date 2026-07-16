import re
from typing import Any


APPROVED_STATUSES = {
    "processando",
    "enviado",
    "entregue",
    "troca_solicitada",
    "reembolsado",
}
ORDER_RE = re.compile(r"^PED-\d{4,}$")


def safe_order_read_filter(tool_input: dict[str, Any], owner: str) -> dict[str, str]:
    """Reconstrói o filtro inteiro; nenhuma opção fornecida pelo modelo sobrevive."""
    order_id = str(tool_input.get("order_id", "")).upper().strip()
    if not ORDER_RE.fullmatch(order_id):
        raise ValueError("order_id inválido")
    return {"order_id": order_id, "owner_customer_key": owner}


def safe_order_update(
    tool_input: dict[str, Any], owner: str
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    query = safe_order_read_filter(tool_input, owner)
    status = str(tool_input.get("status", "")).lower().strip()
    if status not in APPROVED_STATUSES:
        raise ValueError("status não permitido")
    return query, {"$set": {"status": status}}


def safe_invoice_filter(tool_input: dict[str, Any], owner: str) -> dict[str, str]:
    invoice_id = str(tool_input.get("invoice_id", "")).upper().strip()
    if not re.fullmatch(r"FAT-\d{4,}", invoice_id):
        raise ValueError("invoice_id inválido")
    return {"invoice_id": invoice_id, "owner_customer_key": owner}


def safe_shipment_filter(tool_input: dict[str, Any], owner: str) -> dict[str, str]:
    order_id = str(tool_input.get("order_id", "")).upper().strip()
    if not ORDER_RE.fullmatch(order_id):
        raise ValueError("order_id inválido")
    return {"order_id": order_id, "owner_customer_key": owner}


def public_document(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    return {key: value for key, value in document.items() if key != "_id"}

