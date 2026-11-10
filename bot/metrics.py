from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    target: int
    source: str


# Agrega una métrica aquí; se incluirá en el panel y en los comandos al reiniciar.
METRICS = (
    Metric("members", "Personas en el servidor", 1000, "members"),
    Metric("boosts", "Boosts", 6, "boosts"),
    Metric("raptor", "Raptors", 10, "role"),
    Metric("cera", "Ceras", 7, "role"),
    Metric("carno", "Carnos", 5, "role"),
    Metric("spino", "Spinos", 3, "role"),
    Metric("trex", "T-rex", 2, "role"),
    Metric("deino", "Deinosuchus", 1, "role"),
)
METRICS_BY_KEY = {metric.key: metric for metric in METRICS}
