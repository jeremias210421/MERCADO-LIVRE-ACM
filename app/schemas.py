"""
Pydantic schemas for request validation.
"""
from typing import Optional, Union, List
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date


class MotoristaCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    telefone: Optional[str] = Field(None, max_length=20)

    @field_validator('nome')
    @classmethod
    def validate_nome(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Nome é obrigatório')
        return v


class MotoristaUpdate(MotoristaCreate):
    pass


class ScanCreate(BaseModel):
    rota_id: str = Field(..., min_length=1)
    motorista_id: str = Field(..., min_length=1)
    codigo_pacote: str = Field(..., min_length=1, max_length=50)
    formato: Optional[str] = Field('QR_CODE', max_length=20)
    endereco: Optional[str] = None
    is_valid: bool = True
    escaneado_em: Optional[str] = None


class ScansBatch(BaseModel):
    """Accepts either {"scans": [...]} or [...] directly."""
    scans: List[ScanCreate] = Field(default_factory=list, min_length=1, max_length=500)

    @model_validator(mode='before')
    @classmethod
    def accept_list_or_object(cls, data):
        if isinstance(data, list):
            return {'scans': data}
        return data


class RotaAssign(BaseModel):
    rota_id: str = Field(..., min_length=1)
    motorista_id: str = Field(..., min_length=1)


class PendenteFilter(BaseModel):
    motorista_id: Optional[str] = None
    data: Optional[date] = None