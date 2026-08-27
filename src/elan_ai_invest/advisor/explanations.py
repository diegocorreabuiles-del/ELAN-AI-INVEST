from collections.abc import Mapping


def explain(recommendation: Mapping[str, object]) -> str:

    return (
        f"ELAN recomienda comprar "
        f"{recommendation['symbol']} "
        f"porque actualmente presenta "
        f"el mejor score disponible."
    )
