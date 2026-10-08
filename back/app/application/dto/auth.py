from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    name: str
    email: str
    password: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str = field(repr=False)
