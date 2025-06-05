Adds some holism to your charm.


# Basic usage: reconciler pattern

```python
import ops
class MyCharm(ops.CharmBase):
    def reconcile(self):
        print("I will be called exactly once per juju event")

if __name__ == '__main__':
    from holism import holism
    with holism(MyCharm) as h:
        h.charm.reconcile()
```

# Pro usage: reconciler pattern and deltas

```python
import ops


class MyCharm(ops.CharmBase):
    def __init__(self, fw):
        super().__init__(fw)
        fw.observe(self.on.update_status, self._on_smh)
        
    def _on_smh(self, e):
        print("I will be called first")
        
    def reconcile(self):
        print("I will be called last, still only once")


if __name__ == '__main__':
    from holism import holism

    with holism(MyCharm) as h:
        h.charm.reconcile()
```


# Sensei usage: functional reconcilers

```python
import ops
from lib...ingress import IngressPerAppRequirer
        
        
def reconcile(app:ops.Application, unit:ops.Unit, relation:ops.Relation):
    relation.data[app]['foo'] = 'bar!'
    unit.status = ops.ActiveStatus("I've been reconciled!")

    # nothing prevents you from using regular ops.Object s in here,
    # so long as their API allows it...
    ipa = IngressPerAppRequirer(..., relation=relation)
    ipa.get_address()

if __name__ == '__main__':
    from holism import holism
    
    with holism() as h:
        reconcile(h.app, h.unit, h.model.get_relation("ingress"))
```


## Controlling when the `collect-*-status` are emitted

```python
if __name__ == '__main__':
    from holism import holism
    
    with holism(evaluate_status=False) as h:
        # do something
        h.evaluate_status()
        # do something else
```


## Controlling whether 'regular' event emission occurs at all

```python
import ops 

class MyCharm(ops.CharmBase):
    def __init__(self, fw):
        super().__init__(fw)
        fw.observe(self.on.update_status, self._on_smh)
        
    def _on_smh(self, e):
        print("I will not be called at all!")
        
if __name__ == '__main__':
    from holism import holism
    
    with holism(MyCharm, emit=False) as h:
        # no events will be emitted on the charm
        pass
```
