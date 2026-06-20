from django.test import TestCase

from advisor.packages import build_advisor_packages, build_package_table
from army_books.models import Faction, Unit, UnitUpgradeOption, UnitUpgradeSection, UnitWeaponSlot, Weapon


class AdvisorPackageTests(TestCase):
    def setUp(self):
        self.faction = Faction.objects.create(name="Kingdom of Angels", version="3.5.3")
        self.weapon = Weapon.objects.create(
            name="Great Weapon",
            range=0,
            attacks=2,
            attacks_string="A2",
            ap=2,
        )

    def test_builds_default_size_package_with_roles_and_force_org_hints(self):
        unit = self._unit(
            name="Sky Guard",
            points=120,
            min_models=5,
            max_models=10,
            default_models=5,
            special_rules={"Scout": True, "Flying": True},
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        package = next(candidate for candidate in packages if candidate.unit_id == unit.id)
        self.assertEqual(package.package_id, f"u{unit.id}-base")
        self.assertEqual(package.model_count, 5)
        self.assertEqual(package.points, 120)
        self.assertEqual(package.selected_upgrade_ids, [])
        self.assertIn("mobility", package.role_tags)
        self.assertIn("core", package.role_tags)
        self.assertFalse(package.exceeds_group_cap)

    def test_builds_upgrade_packages_with_computed_points(self):
        unit = self._unit(name="Paladins", points=180, tough=3)
        section = UnitUpgradeSection.objects.create(
            unit=unit,
            section_uid="paladin-upgrades",
            label="Paladin Upgrades",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="blessed-weapons",
            label="Blessed Weapons",
            cost=20,
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        upgrade_package = next(
            candidate for candidate in packages if candidate.selected_upgrade_ids == [option.id]
        )
        self.assertEqual(upgrade_package.package_id, f"u{unit.id}-o{option.id}")
        self.assertEqual(upgrade_package.points, 200)
        self.assertIn("anti-tough", upgrade_package.role_tags)

    def test_package_table_renders_package_ids_constraints_and_roles(self):
        self._unit(name="Rangers", points=100, special_rules={"Fast": True})

        table = build_package_table(build_advisor_packages(self.faction.id, point_limit=750))

        self.assertIn(
            "| Package | Unit | Pts | Models | Q | Def | T | AP | Upgrades | Roles | Aura | Embed | Legal |",
            table,
        )
        self.assertIn("u", table)
        self.assertIn("mobility", table)
        self.assertIn("ok", table)

    def test_packages_mark_aura_upgrades_and_embedding_roles(self):
        host = self._unit(
            name="Guardians",
            points=90,
            min_models=5,
            max_models=10,
            default_models=5,
        )
        hero = self._unit(
            name="Champion",
            points=75,
            special_rules={"Hero": True},
        )
        section = UnitUpgradeSection.objects.create(
            unit=hero,
            section_uid="champion-aura",
            label="Take Aura",
        )
        option = UnitUpgradeOption.objects.create(
            section=section,
            option_uid="swift-aura",
            label="Swift Aura",
            cost=10,
            gains=[{"content": [{"name": "Swift Aura", "type": "ArmyBookRule"}]}],
        )

        packages = build_advisor_packages(self.faction.id, point_limit=750)

        host_package = next(package for package in packages if package.unit_id == host.id)
        hero_package = next(package for package in packages if package.selected_upgrade_ids == [option.id])
        self.assertTrue(host_package.can_host_embedded_hero)
        self.assertFalse(host_package.can_embed_as_hero)
        self.assertTrue(hero_package.can_embed_as_hero)
        self.assertFalse(hero_package.can_host_embedded_hero)
        self.assertEqual(hero_package.aura_rules, ("Swift Aura",))

    def _unit(
        self,
        *,
        name: str,
        points: int,
        tough: int = 1,
        min_models: int = 1,
        max_models: int | None = 1,
        default_models: int = 1,
        special_rules=None,
    ) -> Unit:
        unit = Unit.objects.create(
            faction=self.faction,
            name=name,
            quality=4,
            defense=5,
            tough=tough,
            points=points,
            min_models=min_models,
            max_models=max_models,
            default_models=default_models,
            special_rules=special_rules or {},
        )
        UnitWeaponSlot.objects.create(unit=unit, weapon=self.weapon, is_default=True)
        return unit
