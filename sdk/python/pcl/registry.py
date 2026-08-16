"""Local file-backed capability registry."""

from __future__ import annotations

import json
from pathlib import Path

from pcl.models import CapabilityDeclaration, CapabilityOffer, Entity


class Registry:
    """In-memory registry loaded from a directory structure."""

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.declarations: dict[str, CapabilityDeclaration] = {}
        self.offers: list[CapabilityOffer] = []

    @classmethod
    def load(cls, root: str | Path) -> Registry:
        root = Path(root)
        registry = cls()

        entities_dir = root / "entities"
        if entities_dir.is_dir():
            for path in sorted(entities_dir.glob("*.json")):
                entity = Entity.from_file(path)
                registry.entities[entity.id] = entity

        declarations_dir = root / "declarations"
        if declarations_dir.is_dir():
            for path in sorted(declarations_dir.glob("*.json")):
                decl = CapabilityDeclaration.from_file(path)
                registry.declarations[decl.id] = decl

        offers_dir = root / "offers"
        if offers_dir.is_dir():
            for path in sorted(offers_dir.glob("*.json")):
                registry.offers.append(CapabilityOffer.from_file(path))

        return registry

    def register_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def register_declaration(self, declaration: CapabilityDeclaration) -> None:
        self.declarations[declaration.id] = declaration

    def register_offer(self, offer: CapabilityOffer) -> None:
        self.offers.append(offer)

    def get_declaration_for_offer(self, offer: CapabilityOffer) -> CapabilityDeclaration | None:
        return self.declarations.get(offer.declaration_id)

    def load_from_flat_directory(self, directory: str | Path) -> None:
        """Load mixed JSON documents from a single directory (by pcl shape)."""
        directory = Path(directory)
        for path in sorted(directory.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if "semantic_type" in data and "execution" in data:
                decl = CapabilityDeclaration.model_validate(data)
                self.declarations[decl.id] = decl
            elif "declaration_id" in data and "state" in data:
                self.offers.append(CapabilityOffer.model_validate(data))
            elif "goal" in data:
                continue
            elif "id" in data:
                self.entities[Entity.model_validate(data).id] = Entity.model_validate(data)
