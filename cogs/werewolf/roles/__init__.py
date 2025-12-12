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
	"cogs.werewolf.roles.villagers.mayor",
	"cogs.werewolf.roles.villagers.idiot",
	"cogs.werewolf.roles.villagers.elder",
	"cogs.werewolf.roles.villagers.scapegoat",
	"cogs.werewolf.roles.villagers.guard",
	"cogs.werewolf.roles.villagers.raven",
	"cogs.werewolf.roles.werewolves.werewolf",
	"cogs.werewolf.roles.werewolves.white_werewolf",
	"cogs.werewolf.roles.neutrals.pied_piper",
	"cogs.werewolf.roles.neutrals.pyromaniac",
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
