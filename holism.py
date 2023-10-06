import types
from dataclasses import dataclass
from itertools import chain
from typing import Union, Dict, List

import ops
import ops.testing
from ops import Framework


@dataclass
class _RelationState:
    """Represents the state of a relation in juju."""
    endpoint: str
    id: int

    joining_units: List[str] = ()
    departing_units: List[str] = ()
    is_breaking: bool = False


class Reductionism(RuntimeError):  # lol
    """Base class for all holistic errors."""


class RelationNotFoundError(Reductionism):
    """Raised when a relation is not found in stored state."""


class Holism(ops.Object):
    """Adds some holism to your charm.

    Usage:
    >>> from ...holism import Holism
    >>> holism = Holism()
    ...
    >>> @holism
    >>> class MyCharm(ops.CharmBase):
    >>>     ...
    >>>     def _some_hook(self, _):
    >>>         if holism.get_relation(e.relation).is_departing or holism.get_relation(e.relation).is_dying:
    >>>             pass
    """
    _stored = ops.StoredState()

    def __init__(self):
        pass

    @property
    def relations(self) -> Dict[str, _RelationState]:
        """Mapping from relation endpoints to their known state."""
        return {endpoint: _RelationState(**meta) for endpoint, meta in
                self._stored.relations.items()}

    def get_relation(self, relation: Union[str, ops.Relation]):
        relation_name = relation if isinstance(relation, str) else relation.name
        try:
            return self.relations[relation_name]
        except KeyError:
            raise RelationNotFoundError(relation_name)

    def __call__(self, cls: ops.testing.CharmType):
        """Set up holism with this charm class.

        This makes Holism usable as a charm class decorator.
        """

        def holistic_init(charm):
            ops.Object.__init__(
                self,
                parent=charm,
                key="__holism__")

            self._stored.set_default(
                relations={}
            )

            self._setup_observers(charm)

        original_init = cls.__init__

        def init(_self, *args, **kwargs):
            original_init(_self, *args, **kwargs)
            holistic_init(_self)

        cls.__init__ = init
        return cls

    def _setup_observers(self, charm: ops.testing.CharmType):
        """Register observers on the charm to be able to monitor its state."""
        observe = self.framework.observe
        observed_events = []
        for endpoint in chain(charm.meta.provides, charm.meta.requires, charm.meta.peers):
            for event in [charm.on[endpoint].relation_created,
                          charm.on[endpoint].relation_changed,
                          charm.on[endpoint].relation_broken,
                          charm.on[endpoint].relation_joined,
                          charm.on[endpoint].relation_departed]:
                observe(event, self._process_relation)
                observed_events.append(event)

        for event in charm.on.events().values():
            # event is a good chance to clean-up relations previously marked as `breaking`,
            # and remove units from the joining/departing lists
            observe(event, self._update_transients)

    def _process_relation(self, e: ops.RelationEvent):
        if isinstance(e, ops.charm.RelationCreatedEvent):
            self._create(e.relation)
        elif isinstance(e, ops.charm.RelationBrokenEvent):
            self._break(e.relation)
        elif isinstance(e, ops.charm.RelationJoinedEvent):
            self._join(e.relation, e.unit)
        elif isinstance(e, ops.charm.RelationDepartedEvent):
            self._depart(e.relation, e.unit)
        else:  # ops.charm.RelationChangedEvent = no-op
            pass

        self._update_transients(e)

    def _create(self, relation: ops.Relation):
        self._stored.relations[relation.name] = {
            "id": relation.id,
            "endpoint": relation.name,
        }

    def _break(self, relation: ops.Relation):
        state = self._stored.relations[relation.name]
        state['is_breaking'] = True

    def _join(self, relation: ops.Relation, unit: ops.Unit):
        state = self._stored.relations[relation.name]
        state['joining_units'] += (unit.name,)

    def _depart(self, relation: ops.Relation, unit: ops.Unit):
        state = self._stored.relations[relation.name]
        state['departing_units'] += (unit.name,)

    def _update_transients(self, e: ops.EventBase):
        self._forget_departed_and_joined_units(e)
        self._forget_broken_relations(e)

    def _forget_departed_and_joined_units(self, e: ops.EventBase):
        keep_joining = keep_departing = None

        # if we are processing a relation-joined event about this relation, the unit is still joining
        if isinstance(e, ops.charm.RelationJoinedEvent):
            keep_joining = e.unit.name
        # same for departing
        if isinstance(e, ops.charm.RelationDepartedEvent):
            keep_departing = e.unit.name

        for relation, meta in self.relations.items():
            meta.joining_units = tuple(u for u in meta.joining_units if u != keep_joining)
            meta.departing_units = tuple(u for u in meta.departing_units if u != keep_departing)

    def _forget_broken_relations(self, e: ops.EventBase):
        for relation, meta in self.relations.items():
            # if we are processing an event about this relation, we're not ready to forget it just yet
            if isinstance(e, ops.charm.RelationEvent) and e.relation.name == relation:
                continue

            if meta.is_breaking:
                self._forget(relation)

    def _forget(self, relation: str):
        del self._stored.relations[relation]

    @staticmethod
    def _to_unit_name(unit: Union[str, ops.Unit]) -> str:
        return unit if isinstance(unit, str) else unit.name

    def is_joining(self, relation: Union[str, ops.Relation], unit: Union[str, ops.Unit]):
        """Last we heard, was this unit joining this relation?"""
        relation = self.get_relation(relation)
        return self._to_unit_name(unit) in relation.joining_units

    def is_departing(self, relation: Union[str, ops.Relation], unit: Union[str, ops.Unit]):
        """Last we heard, was this unit departing this relation?"""
        relation = self.get_relation(relation)
        return self._to_unit_name(unit) in relation.departing_units

    def is_alive(self, relation: Union[str, ops.Relation]):
        """Is this relation (still) alive?

        If we have received a relation-broken at least "one event ago", then the relation is dead.
        Otherwise, it's alive.
        """

        try:
            self.get_relation(relation)
        except RelationNotFoundError:
            return False
        return True

    def is_breaking(self, relation: Union[str, ops.Relation]):
        """Last we heard, was this relation breaking?"""
        return self.get_relation(relation).is_breaking
