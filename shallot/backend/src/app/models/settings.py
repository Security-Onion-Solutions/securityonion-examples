from datetime import datetime
from sqlalchemy import Column, String, Integer
from sqlalchemy.sql import func

from ..database import Base
from ..core.security import encrypt_value, decrypt_value


class Settings(Base):
    """Model for storing encrypted application settings."""

    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    encrypted_value = Column(String, nullable=False)
    description = Column(String, nullable=True)
    updated_at = Column(Integer, default=lambda: int(datetime.now().timestamp()), onupdate=lambda: int(datetime.now().timestamp()))

    @property
    def value(self) -> str:
        """Get decrypted value."""
        try:
            if not self.encrypted_value:
                return ""
            decrypted = str(decrypt_value(str(self.encrypted_value)))
            print(f"Successfully decrypted value for key {self.key}")
            return decrypted
        except Exception as e:
            print(f"Error decrypting value for key {self.key}: {str(e)}")
            print(f"Encrypted value was: {self.encrypted_value}")
            raise

    @value.setter
    def value(self, plain_value: str) -> None:
        """Set encrypted value."""
        try:
            if plain_value is None:
                print(f"Setting empty value for key {self.key}")
                setattr(self, "encrypted_value", "")
            else:
                print(f"Encrypting value for key {self.key}")
                encrypted = str(encrypt_value(str(plain_value)))
                print(f"Successfully encrypted value for key {self.key}")
                setattr(self, "encrypted_value", encrypted)
        except Exception as e:
            print(f"Error encrypting value for key {self.key}: {str(e)}")
            print(f"Plain value was: {plain_value}")
            raise

    def __repr__(self) -> str:
        return f"<Settings key={self.key} updated_at={self.updated_at}>"
