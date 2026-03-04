from dataclasses import dataclass


@dataclass
class CepAlert:
    id: int
    rule: str
    severity: str
    message: str
    created_at: str

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'rule': self.rule,
            'severity': self.severity,
            'message': self.message,
            'created_at': self.created_at,
        }
