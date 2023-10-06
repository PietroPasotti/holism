import pytest
from ops import CharmBase
from scenario import Context, State, Relation

from holism import Holism, RelationNotFoundError

holism = Holism()


@holism
class MyCharm(CharmBase):
    pass


def test_holism():
    ctx = Context(MyCharm, meta={'name': 'test-holism'})
    with ctx.manager("start", State()) as mgr:
        assert not holism.relations


def test_relation_create():
    ctx = Context(
        MyCharm,
        meta={'name': 'test-holism',
              "requires": {"foo": {"interface": "bar"}}}
    )
    foo = Relation("foo")
    with ctx.manager(foo.created_event, State(relations=[foo])) as mgr:
        with pytest.raises(RelationNotFoundError):
            _foo = holism.get_relation('foo')

        mgr.run()

        _foo = holism.get_relation('foo')
        assert _foo.endpoint == 'foo'
        assert not _foo.joining_units
        assert not _foo.departing_units
