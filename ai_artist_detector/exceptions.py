class ProjectError(Exception):
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(f"{key}={value!r}" for key, value in self.__dict__.items())})'


class InvalidConfigTypeError(ProjectError, TypeError): ...


class RowNotFoundError(ProjectError): ...


class RateLimitExceededError(ProjectError):
    def __init__(self, body: str) -> None:
        self.body = body


class InvalidYoutubeMusicAccountTypeError(ProjectError):
    def __init__(self, youtube_id: str, reason: str) -> None:
        self.youtube_id = youtube_id
        self.reason = reason


class MatchingNotImplementedError(ProjectError): ...


class PlaylistsNotFoundError(ProjectError): ...


class SinglesNotFoundError(ProjectError): ...


class NoSongsFoundError(ProjectError): ...
