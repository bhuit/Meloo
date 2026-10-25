"""State for Ctrl + file dragging. No text, clipboard access or keyboard hooks."""
from dataclasses import dataclass


@dataclass
class DragGesture:
    origin: tuple[int, int] | None = None
    started_at: float = 0
    eligible: bool = False
    opened: bool = False
    cancelled: bool = False
    session: int = 0

    def update(self, *, pressed, ctrl, altgr, escape, source_ok, position, now, enabled=True):
        if not enabled or not pressed:
            was_open = self.opened
            self.origin = None
            self.opened = self.cancelled = self.eligible = False
            return "release" if was_open else None
        if self.origin is None:
            self.origin = position
            self.started_at = now
            self.eligible = source_ok
            self.session += 1
        if escape:
            self.cancelled = True
            return "cancel" if self.opened else None
        if self.opened or self.cancelled or not self.eligible or altgr or not ctrl:
            return None
        distance = abs(position[0] - self.origin[0]) + abs(position[1] - self.origin[1])
        if distance < 12 or now - self.started_at < .12:
            return None
        self.opened = True
        return "open"
