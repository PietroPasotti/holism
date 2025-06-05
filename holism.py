import sys
import typing
from contextlib import contextmanager
from typing import Callable
from unittest.mock import patch

import ops
import scenario


class Reductionism(RuntimeError):  # lol
    """Base class for all holistic errors."""


class _Manager(ops._main._Manager):
    def run(
        self,
        emit: bool = True,
        evaluate_status: bool = True,
    ):
        """Emit and then commit the framework."""
        try:
            if emit:
                self._emit(evaluate_status=evaluate_status)
            if not emit and evaluate_status:
                raise Reductionism(f"invalid args combo: {emit=}, {evaluate_status=}")

            # interrupt execution, to give holism a chance to do stuff
            # before we commit, evaluate status and close
            yield

            self._commit()
            self._close()
        finally:
            self.framework.close()

    def _emit(self, evaluate_status: bool = False):
        """Emit the event on the charm."""
        # TODO: Remove the collect_metrics check below as soon as the relevant
        #       Juju changes are made. Also adjust the docstring on
        #       EventBase.defer().
        #
        # Skip reemission of deferred events for collect-metrics events because
        # they do not have the full access to all hook tools.
        if not self.dispatcher.is_restricted_context():
            # Re-emit any deferred events from the previous run.
            self.framework.reemit()

        # Emit the Juju event.
        self._emit_charm_event(self.dispatcher.event_name)
        # Emit collect-status events.
        if evaluate_status:
            self.evaluate_status()

    def evaluate_status(self):
        """Emit collect-*-status."""
        ops.charm._evaluate_status(self.charm)


@contextmanager
def holism(
    charm_class: typing.Type[ops.CharmBase] = None,
    use_juju_for_storage: bool = False,
    emit: bool = True,
    evaluate_status: bool = True,
    _mgr: scenario.context.Manager = None,
):
    """Add some holism to your charm."""
    framework = None
    charm_instance = None
    if _mgr:
        # we're testing
        # h = _Holism(
        charm_class = _mgr.charm.__class__
        charm_instance = _mgr.charm
        framework = _mgr.ops.framework

    # this is largely copied from ops._main.main
    manager = None
    try:
        manager = _mgr or _Manager(
            charm_class or ops.CharmBase, use_juju_for_storage=use_juju_for_storage
        )
        with manager.run(emit=emit, evaluate_status=evaluate_status):
            h = _Holism(
                charm=charm_instance or manager.charm,
                framework=framework or manager.framework,
            )
            yield h

    except ops._main._Abort as e:
        sys.exit(e.exit_code)
    finally:
        if manager:
            manager._destroy()


class _Holism:
    """Holistic framework context."""

    def __init__(self, framework: ops.framework.Framework, charm: ops.CharmBase):
        self.framework = framework

        self.model = charm.model
        self.meta = charm.meta
        self.charm_dir = charm.charm_dir
        self.charm = charm
        self.unit = charm.unit
        self.app = charm.app
        self.config = charm.config

        self.evaluate_status = lambda: ops.charm._evaluate_status(charm)


class testing:
    state_out: scenario.State = None

    @contextmanager
    @staticmethod
    def mgr(charm_class: typing.Type[ops.CharmBase], charm_meta: dict):
        """Helper to set up a mgr fixture."""

        # we use scenario to help us set up a viable environ
        # however, we also don't want to emit any event since we're in charge of that
        @contextmanager
        def patched_run(self: scenario.Manager, emit: bool, **kwargs):
            self._emitted = True
            if emit:
                self.ops.run()
            yield

        _ctx = scenario.Context(charm_class, meta=charm_meta)
        with patch.object(scenario.Manager, "run", new=patched_run):
            with _ctx(_ctx.on.update_status(), scenario.State()) as mgr:
                mgr._destroy = lambda: None
                yield mgr

                # wrap up Runtime.exec() so that we can gather the output state
                mgr._wrapped_ctx.__exit__(None, None, None)
            testing.state_out = mgr._ctx._output_state

    @contextmanager
    @staticmethod
    def holism(
        charm_class: typing.Type[ops.CharmBase] = None,
        use_juju_for_storage: bool = False,
        emit: bool = True,
        evaluate_status: bool = True,
        # testing-specific args
        meta: dict = None,
    ):
        """Helper to set up a holism fixture for testing."""
        charm_class = charm_class or ops.CharmBase
        meta = meta or {"name": "robin"}
        with testing.mgr(charm_class, meta) as mgr:
            with holism(
                _mgr=mgr,
                use_juju_for_storage=use_juju_for_storage,
                emit=emit,
                evaluate_status=evaluate_status,
            ) as h:
                yield h
