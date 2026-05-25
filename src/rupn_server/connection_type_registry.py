from __future__ import annotations

from rupn_server.connection_type_profile import ConnectionTypeProfile


class ConnectionTypeRegistry:
    _profiles = {
        "wbstream": ConnectionTypeProfile(name="wbstream", carrier="wbstream", transport="datachannel"),
        "telemost": ConnectionTypeProfile(name="telemost", carrier="telemost", transport="vp8channel"),
    }

    @classmethod
    def default(cls) -> ConnectionTypeProfile:
        return cls._profiles["telemost"]

    @classmethod
    def names(cls) -> tuple[str, ...]:
        return tuple(cls._profiles.keys())

    @classmethod
    def resolve(cls, value: str | None) -> ConnectionTypeProfile:
        normalized = (value or cls.default().name).strip().lower()
        try:
            return cls._profiles[normalized]
        except KeyError as error:
            allowed = ", ".join(cls.names())
            raise ValueError(f"unknown connection type: {normalized}; allowed: {allowed}") from error
