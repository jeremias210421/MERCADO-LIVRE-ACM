"""
Pydantic schemas for request validation.
"""

from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


class MotoristaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    telefone: str | None = Field(None, max_length=20)

    @field_validator("nome")
    @classmethod
    def validate_nome(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome é obrigatório")
        return v


class MotoristaUpdate(MotoristaCreate):
    pass


class ScanCreate(BaseModel):
    """Bipagem do app. Aceita legado (FKs) ou texto (app resolve FKs no servidor).

    Legado Android: rota_id + motorista_id + codigo_pacote.
    PWA/atual: code + route + operator_name (+ session_date).
    """

    rota_id: str | None = None
    motorista_id: str | None = None
    codigo_pacote: str | None = Field(None, max_length=80)
    code: str | None = Field(None, max_length=80)
    route: str | None = Field(None, max_length=40)
    rota: str | None = Field(None, max_length=40)
    operator_name: str | None = Field(None, max_length=100)
    operator: str | None = Field(None, max_length=100)
    session_date: str | None = Field(None, max_length=20)
    formato: str | None = Field("QR_CODE", max_length=20)
    format: str | None = Field(None, max_length=20)
    endereco: str | None = None
    is_valid: bool = True
    escaneado_em: str | None = None
    scanned_at: str | None = None

    @model_validator(mode="after")
    def exige_codigo(self):
        code = (self.codigo_pacote or self.code or "").strip()
        if not code:
            raise ValueError("codigo_pacote/code é obrigatório")
        return self


class ScansBatch(BaseModel):
    """Accepts either {"scans": [...]} or [...] directly."""

    scans: list[ScanCreate] = Field(default_factory=list, min_length=1, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def accept_list_or_object(cls, data):
        if isinstance(data, list):
            return {"scans": data}
        return data


class RotaAssign(BaseModel):
    rota_id: str = Field(..., min_length=1)
    motorista_id: str = Field(..., min_length=1)


class PendenteFilter(BaseModel):
    motorista_id: str | None = None
    data: date | None = None
