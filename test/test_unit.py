import ops
from ops import CharmBase, Framework

from holism import testing, _Holism


def test_event_emission():
    class MyCharm(CharmBase):
        called = False

        def __init__(self, fw):
            super().__init__(fw)
            fw.observe(self.on.update_status, self._on_smh)

        def _on_smh(self, e):
            self.called = True

    with testing.holism(MyCharm) as h:
        pass

    assert h.charm.called


def test_reconciler():
    class MyCharm(CharmBase):
        called = False
        reconciled = False

        def __init__(self, fw):
            super().__init__(fw)
            fw.observe(self.on.update_status, self._on_smh)

        def _on_smh(self, e):
            self.called = True

        def reconcile(self):
            self.reconciled = True

    with testing.holism(MyCharm) as h:
        h.charm.reconcile()

    assert h.charm.called
    assert h.charm.reconciled


def test_reconciler_no_emit():
    class MyCharm(CharmBase):
        called = False
        reconciled = False

        def __init__(self, fw):
            super().__init__(fw)
            fw.observe(self.on.update_status, self._on_smh)

        def _on_smh(self, e):
            self.called = True

        def reconcile(self):
            self.reconciled = True

    with testing.holism(MyCharm, emit=False) as h:
        h.charm.reconcile()

    assert not h.charm.called
    assert h.charm.reconciled


def test_state():
    class MyCharm(CharmBase):
        pass

    with testing.holism(MyCharm, emit=False) as h:
        h: _Holism

    assert testing.state_out


def test_status_holistically_set():
    class MyCharm(CharmBase):
        pass

    status = ops.ActiveStatus("foo")

    with testing.holism(MyCharm, emit=False) as h:
        h: _Holism
        h.charm.unit.status = status

    assert testing.state_out.unit_status == status


def test_status_charm_set():
    status = ops.ActiveStatus("foo")

    class MyCharm(CharmBase):
        def __init__(self, framework: Framework):
            super().__init__(framework)
            self.unit.status = status

    with testing.holism(MyCharm, emit=False) as h:
        h: _Holism

    assert testing.state_out.unit_status == status
