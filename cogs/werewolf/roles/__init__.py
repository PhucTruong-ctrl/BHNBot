"""Role registry and helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Dict, Iterable, Optional, Type

from .base import Alignment, Expansion, Role


ROLE_REGISTRY: Dict[str, Type[Role]] = {}
_ROLE_MODULES = (
	"cogs.werewolf.roles.villagers.villager",
	"cogs.werewolf.roles.villagers.seer",
	"cogs.werewolf.roles.villagers.witch",
	"cogs.werewolf.roles.villagers.hunter",
	"cogs.werewolf.roles.villagers.cupid",
	"cogs.werewolf.roles.villagers.little_girl",
	"cogs.werewolf.roles.villagers.thief",
	"cogs.werewolf.roles.villagers.wolf_hybrid",
	"cogs.werewolf.roles.villagers.wild_child",
	"cogs.werewolf.roles.villagers.mayor",
	"cogs.werewolf.roles.villagers.idiot",
	"cogs.werewolf.roles.villagers.elder",
	"cogs.werewolf.roles.villagers.scapegoat",
	"cogs.werewolf.roles.villagers.guard",
	"cogs.werewolf.roles.villagers.raven",
	"cogs.werewolf.roles.villagers.two_sisters",
	"cogs.werewolf.roles.villagers.knight",
	"cogs.werewolf.roles.villagers.angel_of_death",
	"cogs.werewolf.roles.villagers.moon_maiden",
	"cogs.werewolf.roles.villagers.hypnotist",
	"cogs.werewolf.roles.villagers.pharmacist",
	"cogs.werewolf.roles.villagers.assassin",
	"cogs.werewolf.roles.villagers.cavalry",
	"cogs.werewolf.roles.villagers.judge",
	"cogs.werewolf.roles.villagers.actor",
	"cogs.werewolf.roles.werewolves.werewolf",
	"cogs.werewolf.roles.werewolves.big_bad_wolf",
	"cogs.werewolf.roles.werewolves.demon_wolf",
	"cogs.werewolf.roles.werewolves.fire_wolf",
	"cogs.werewolf.roles.werewolves.wolf_brother",
	"cogs.werewolf.roles.werewolves.wolf_sister",
	"cogs.werewolf.roles.neutrals.pied_piper",
	"cogs.werewolf.roles.neutrals.pyromaniac",
	"cogs.werewolf.roles.neutrals.white_werewolf",
	"cogs.werewolf.roles.neutrals.avenger",
)


def register_role(cls: Type[Role]) -> Type[Role]:
	"""Decorator used by role modules to register themselves."""

	ROLE_REGISTRY[cls.metadata.name] = cls
	return cls


def get_role_class(name: str) -> Type[Role]:
	return ROLE_REGISTRY[name]


def iter_role_classes(
	*,
	alignment: Optional[Alignment] = None,
	expansions: Optional[Iterable[Expansion]] = None,
) -> Iterable[Type[Role]]:
	allowed_expansions = set(expansions) if expansions else None
	for role_cls in ROLE_REGISTRY.values():
		if alignment and role_cls.metadata.alignment != alignment:
			continue
		if allowed_expansions and role_cls.metadata.expansion not in allowed_expansions:
			continue
		yield role_cls


def load_all_roles() -> None:
	for module_path in _ROLE_MODULES:
		import_module(module_path)
