Adds some holism to your charm.

    from ...holism import Holism
    holism = Holism()
        @holism
    class MyCharm(ops.CharmBase):
        ...
        def _some_hook(self, e):
            if holism.get_relation(e.relation).is_departing or holism.get_relation(e.relation).is_dying:
                pass