"""Context-local LLM/embedding usage tracking for investigations and ad-hoc calls."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator, Literal
from uuid import uuid4

from app.ai.pricing import estimate_cost_usd

CallKind = Literal[
    "diagnosis",
    "judge",
    "embedding",
    "pr_review",
    "mcp_ask",
    "performance_host",
    "performance_summary",
    "security",
    "cloud_cost",
    "other",
]

ScopeType = Literal[
    "investigation",
    "pr_review",
    "mcp_ask",
    "performance",
    "security",
    "other",
]


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if self.total_tokens <= 0:
            self.total_tokens = max(0, self.input_tokens) + max(0, self.output_tokens)


@dataclass(slots=True)
class UsageCall:
    provider: str
    model: str
    call_kind: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_usd: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UsageSession:
    scope_type: str
    scope_id: str
    user_id: str | None = None
    agent_type: str | None = None
    default_call_kind: str = "other"
    calls: list[UsageCall] = field(default_factory=list)

    @property
    def input_tokens(self) -> int:
        return sum(call.input_tokens for call in self.calls)

    @property
    def output_tokens(self) -> int:
        return sum(call.output_tokens for call in self.calls)

    @property
    def total_tokens(self) -> int:
        return sum(call.total_tokens for call in self.calls)

    @property
    def estimated_usd(self) -> float | None:
        values = [call.estimated_usd for call in self.calls if call.estimated_usd is not None]
        if not values and not self.calls:
            return None
        if not values:
            # All unknown pricing
            if any(call.provider.lower() == "ollama" for call in self.calls):
                return 0.0
            return None
        return round(sum(values), 8)

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def summary_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_usd": self.estimated_usd,
            "call_count": self.call_count,
            "calls": [call.to_dict() for call in self.calls],
        }


_current_session: ContextVar[UsageSession | None] = ContextVar(
    "llm_usage_session",
    default=None,
)
_current_call_kind: ContextVar[str | None] = ContextVar(
    "llm_usage_call_kind",
    default=None,
)


class UsageTracker:
    """Accumulate provider token usage for the active session."""

    @staticmethod
    def current() -> UsageSession | None:
        return _current_session.get()

    @staticmethod
    def start_session(
        *,
        scope_type: str,
        scope_id: str | None = None,
        user_id: str | None = None,
        agent_type: str | None = None,
        default_call_kind: str = "other",
    ) -> UsageSession:
        session = UsageSession(
            scope_type=scope_type,
            scope_id=(scope_id or str(uuid4())).strip(),
            user_id=str(user_id) if user_id else None,
            agent_type=agent_type,
            default_call_kind=default_call_kind,
        )
        _current_session.set(session)
        return session

    @staticmethod
    def end_session() -> UsageSession | None:
        session = _current_session.get()
        _current_session.set(None)
        _current_call_kind.set(None)
        return session

    @staticmethod
    @contextmanager
    def session(
        *,
        scope_type: str,
        scope_id: str | None = None,
        user_id: str | None = None,
        agent_type: str | None = None,
        default_call_kind: str = "other",
    ) -> Iterator[UsageSession]:
        session = UsageTracker.start_session(
            scope_type=scope_type,
            scope_id=scope_id,
            user_id=user_id,
            agent_type=agent_type,
            default_call_kind=default_call_kind,
        )
        try:
            yield session
        finally:
            UsageTracker.end_session()

    @staticmethod
    @contextmanager
    def call_kind(kind: str) -> Iterator[None]:
        token: Token = _current_call_kind.set(kind)
        try:
            yield
        finally:
            _current_call_kind.reset(token)

    @staticmethod
    def record(
        *,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        call_kind: str | None = None,
        estimated_usd: float | None = None,
    ) -> UsageCall | None:
        session = _current_session.get()
        if session is None:
            return None

        usage = TokenUsage(
            input_tokens=max(0, int(input_tokens or 0)),
            output_tokens=max(0, int(output_tokens or 0)),
            total_tokens=max(0, int(total_tokens or 0)),
        )
        kind = (
            call_kind
            or _current_call_kind.get()
            or session.default_call_kind
            or "other"
        )
        cost = estimated_usd
        if cost is None:
            cost = estimate_cost_usd(
                provider,
                model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
        call = UsageCall(
            provider=(provider or "unknown").strip().lower(),
            model=(model or "").strip(),
            call_kind=kind,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            estimated_usd=cost,
        )
        session.calls.append(call)
        return call
