"""Shared transition field shapes and constants; no runtime state reads."""
from sts2_mcp.output.value_shapes import nullable, TEXT, NUMBER


EVENT_ENTITY = {"id": int, "kind": str, "name": TEXT}
TARGET_ENTITY = {**EVENT_ENTITY, "id": frozenset({int, str})}
POTION_REF = {"slot_index": int, "name": TEXT}
EVENT_SOURCE = {"kind": str, "name": TEXT}
EVENT = {
    "sequence": int, "type": str, "actor": EVENT_ENTITY, "target": EVENT_ENTITY,
    "source": nullable(EVENT_SOURCE), "card": {"id": int, "name": TEXT},
    "hp_loss": NUMBER, "blocked": int, "before": NUMBER, "after": NUMBER,
    "name": TEXT, "autoplay": bool, "change": str, "potion": POTION_REF,
    "relic": {"name": TEXT}, "pile": TEXT,
    "orb": {"name": str}, "slot_index": int,
}
TRANSITION = {"stop_reason": str, "complete": bool, "events": [EVENT]}
