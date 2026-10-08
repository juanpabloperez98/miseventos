from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from typing import Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.exceptions import DomainError, NotFoundError
from app.domain.value_objects import Page, PageRequest
from app.infrastructure.database.base import Base


class Identifiable(Protocol):
    id: int | None


class SqlAlchemyRepository[EntityT: Identifiable, ModelT: Base](ABC):
    model: type[ModelT]
    entity_name: str
    unique_violations: Mapping[str, Callable[[], DomainError]] = {}

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: EntityT) -> EntityT:
        model = self.model()
        self._apply(entity, model)
        self._session.add(model)
        self._flush()
        return self._to_entity(model)

    def get_by_id(self, entity_id: int) -> EntityT | None:
        model = self._session.get(self.model, entity_id)
        return self._to_entity(model) if model is not None else None

    def update(self, entity: EntityT) -> EntityT:
        if entity.id is None:
            raise ValueError(f"Cannot update a non persisted {self.entity_name}")
        model = self._get_model_or_raise(entity.id)
        self._apply(entity, model)
        self._flush()
        return self._to_entity(model)

    def delete(self, entity_id: int) -> None:
        self._session.delete(self._get_model_or_raise(entity_id))
        self._flush()

    @abstractmethod
    def _to_entity(self, model: ModelT) -> EntityT: ...

    @abstractmethod
    def _apply(self, entity: EntityT, model: ModelT) -> None: ...

    def _get_model_or_raise(self, entity_id: int) -> ModelT:
        model = self._session.get(self.model, entity_id)
        if model is None:
            raise NotFoundError.for_entity(self.entity_name)
        return model

    def _paginate(self, statement: Select[ModelT], page: PageRequest) -> Page[EntityT]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = self._session.scalar(count_statement) or 0
        models = self._session.scalars(statement.limit(page.per_page).offset(page.offset))
        return Page(items=[self._to_entity(model) for model in models], total=total, request=page)

    def _flush(self) -> None:
        try:
            self._session.flush()
        except IntegrityError as error:
            domain_error = self._translate_integrity_error(error)
            if domain_error is None:
                raise
            self._session.rollback()
            raise domain_error from error

    def _translate_integrity_error(self, error: IntegrityError) -> DomainError | None:
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        factory = self.unique_violations.get(constraint_name or "")
        return factory() if factory is not None else None
