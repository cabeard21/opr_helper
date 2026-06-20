from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone as datetime_timezone
from typing import Any

from django.utils import timezone

from army_books.models import UnitUpgradeOption, UnitWeaponSlot
from lists.models import ArmyList, ListUnit
from lists.loadouts import selected_or_default_slot
from lists.validation import army_list_points


class ArmyForgeExportError(ValueError):
    """Raised when a list cannot be represented as a native Army Forge save."""


@dataclass(frozen=True)
class ExportRow:
    entry: ListUnit
    copy_index: int
    selection_id: str
    root_selection_id: str


def army_forge_save_json(army_list: ArmyList) -> dict[str, Any]:
    _validate_exportable(army_list)

    modified = _format_timestamp(army_list.updated_at)
    rows = _expanded_rows(army_list)
    native_units = [_export_unit_row(row, army_list) for row in rows]
    army_id = army_list.faction.source_uid
    list_id = _list_id(army_list)

    return {
        "id": list_id,
        "list": {
            "id": list_id,
            "key": _list_key(army_list),
            "name": army_list.name,
            "units": native_units,
            "isCloud": False,
            "forceOrg": True,
            "modified": modified,
            "gameSystem": "aof",
            "modelCount": _model_count(army_list),
            "simpleMode": False,
            "description": "",
            "pointsLimit": army_list.point_limit,
            "campaignMode": False,
            "cloudModified": modified,
            "narrativeMode": False,
            "activationCount": _activation_count(army_list),
        },
        "armyId": army_id,
        "armyIds": [army_id],
        "armyName": army_list.faction.name,
        "modified": modified,
        "favourite": False,
        "gameSystem": "aof",
        "listPoints": army_list_points(army_list),
        "armyFaction": None,
        "saveVersion": 3,
        "armyVersions": [{"armyId": army_id, "version": army_list.faction.version}],
    }


def _validate_exportable(army_list: ArmyList) -> None:
    if not army_list.faction.source_uid:
        raise ArmyForgeExportError(
            "Army Forge export requires a native faction ID. Re-sync army books before exporting."
        )

    for entry in army_list.units.all():
        if not entry.unit.source_uid:
            raise ArmyForgeExportError(
                f"Army Forge export requires a native unit ID for {entry.unit.name}. "
                "Re-sync army books before exporting."
            )

        selected_options = _selected_upgrade_options(entry)
        if selected_options:
            for option in selected_options:
                if not option.option_uid or not option.section.section_uid:
                    raise ArmyForgeExportError(
                        f"Army Forge export requires native upgrade IDs for {entry.unit.name}. "
                        "Re-sync army books before exporting."
                    )
        else:
            slot = selected_or_default_slot(entry)
            if slot and _is_selected_upgrade(slot) and (not slot.option_id or not slot.upgrade_id):
                raise ArmyForgeExportError(
                    f"Army Forge export requires native upgrade IDs for {entry.unit.name}. "
                    "Re-sync army books before exporting."
                )


def _expanded_rows(army_list: ArmyList) -> list[ExportRow]:
    entries = sorted(
        army_list.units.select_related("unit", "parent_entry__unit").all(),
        key=lambda entry: (entry.parent_entry_id is not None, entry.unit.name, entry.id),
    )
    rows: list[ExportRow] = []
    for entry in entries:
        combined_count = max(1, entry.combined_from_count)
        root_selection_id = _selection_id(entry, 0)
        for copy_index in range(combined_count):
            rows.append(
                ExportRow(
                    entry=entry,
                    copy_index=copy_index,
                    selection_id=_selection_id(entry, copy_index),
                    root_selection_id=root_selection_id,
                )
            )
    return rows


def _export_unit_row(row: ExportRow, army_list: ArmyList) -> dict[str, Any]:
    entry = row.entry
    return {
        "id": entry.unit.source_uid,
        "xp": 0,
        "notes": entry.notes or None,
        "armyId": army_list.faction.source_uid,
        "traits": [],
        "combined": entry.combined_from_count > 1,
        "joinToUnit": _join_to_unit(row),
        "selectionId": row.selection_id,
        "selectedUpgrades": _selected_upgrades(entry, row),
    }


def _join_to_unit(row: ExportRow) -> str | None:
    if row.entry.parent_entry_id:
        return _selection_id(row.entry.parent_entry, 0)
    if row.entry.combined_from_count > 1 and row.copy_index > 0:
        return row.root_selection_id
    return None


def _selected_upgrades(entry: ListUnit, row: ExportRow) -> list[dict[str, str]]:
    selected_options = _selected_upgrade_options(entry)
    if selected_options:
        return [
            {
                "optionId": str(option.option_uid),
                "upgradeId": str(option.section.section_uid),
                "instanceId": _native_upgrade_instance_id(entry, option, row.copy_index),
            }
            for option in selected_options
        ]

    slot = selected_or_default_slot(entry)
    if not slot or not _is_selected_upgrade(slot):
        return []

    return [
        {
            "optionId": str(slot.option_id),
            "upgradeId": str(slot.upgrade_id),
            "instanceId": _upgrade_instance_id(entry, slot, row.copy_index),
        }
    ]


def _is_selected_upgrade(slot: UnitWeaponSlot) -> bool:
    return not slot.is_default or slot.upgrade_cost != 0 or bool(slot.option_id or slot.upgrade_id)


def _selected_upgrade_options(entry: ListUnit) -> list[UnitUpgradeOption]:
    return [
        selection.option
        for selection in entry.selected_upgrades.all()
        if selection.option.section.unit_id == entry.unit_id
    ]


def _model_count(army_list: ArmyList) -> int:
    return sum(entry.model_count * max(1, entry.combined_from_count) for entry in army_list.units.all())


def _activation_count(army_list: ArmyList) -> int:
    return sum(1 for entry in army_list.units.all() if entry.parent_entry_id is None)


def _list_id(army_list: ArmyList) -> str:
    return f"opr-{army_list.id}"


def _list_key(army_list: ArmyList) -> str:
    return f"opr-key-{army_list.id}"


def _selection_id(entry: ListUnit, copy_index: int) -> str:
    return f"sel-{entry.id}-{copy_index}"


def _upgrade_instance_id(entry: ListUnit, slot: UnitWeaponSlot, copy_index: int) -> str:
    return f"upg-{entry.id}-{slot.id}-{copy_index}"


def _native_upgrade_instance_id(entry: ListUnit, option: UnitUpgradeOption, copy_index: int) -> str:
    return f"upg-{entry.id}-{option.id}-{copy_index}"


def _format_timestamp(value) -> str:
    if value is None:
        value = timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone=timezone.get_current_timezone())
    return value.astimezone(datetime_timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
