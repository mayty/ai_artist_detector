class ProjectError(Exception):
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(f"{key}={value!r}" for key, value in self.__dict__.items())})'


class InvalidConfigTypeError(ProjectError, TypeError): ...


class ChannelNotFoundError(ProjectError):
    def __init__(self, handle: str) -> None:
        self.handle = handle
