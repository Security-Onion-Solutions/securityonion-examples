from typing import Optional
from pydantic import BaseModel, Field


class SettingBase(BaseModel):
    """Base schema for settings."""

    description: Optional[str] = None


class SettingCreate(SettingBase):
    """Schema for creating a setting."""

    key: str = Field(..., description="Unique identifier for the setting")
    value: str = Field(..., description="Value to be encrypted")


class SettingUpdate(SettingBase):
    """Schema for updating a setting."""

    value: str = Field(..., description="New value to be encrypted")


class Setting(SettingBase):
    """Schema for reading a setting."""

    key: str
    value: str
    updated_at: int

    class Config:
        """Pydantic config."""

        from_attributes = True


class SettingInDB(SettingBase):
    """Schema for database representation."""

    key: str
    encrypted_value: str
    updated_at: int

    class Config:
        """Pydantic config."""

        from_attributes = True
