# Prophet model specs (examples)

These are *examples* of how Prophet can represent models as declarative specs.
They are not wired to code yet; they are meant to clarify what "supporting a family"
means operationally.

A spec should capture:
- task (forecast/risk/etc.)
- data inputs (dataset version URI + feature set)
- model family + hyperparams
- training engine (rayjob/spark/k8sjob)
- serving engine (rayservice/kserve/batch)
- evaluation + gates
