"""TOTP MFA — setup, verify, backup codes."""
import hashlib
import io
import secrets
import base64
from typing import Optional, Tuple
from uuid import UUID

import pyotp
import qrcode

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import MfaCredential, User
from services.crypto_service import encrypt, decrypt, encrypt_json, decrypt_json

APP_NAME = "authYantra"
BACKUP_CODE_COUNT = 10


class MfaService:

    # ------------------------------------------------------------------
    # TOTP setup
    # ------------------------------------------------------------------

    @staticmethod
    def generate_totp_secret() -> str:
        """Return a fresh base32 TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def totp_uri(secret: str, email: str, issuer: str = APP_NAME) -> str:
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

    @staticmethod
    def totp_qr_png_b64(uri: str) -> str:
        """Return a base64-encoded PNG of the QR code (for embedding in JSON)."""
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    @staticmethod
    def generate_backup_codes() -> list[str]:
        """Return BACKUP_CODE_COUNT random 8-char codes (plain text, shown once)."""
        return [secrets.token_hex(4).upper() for _ in range(BACKUP_CODE_COUNT)]

    @staticmethod
    def _hash_backup_code(code: str) -> str:
        return hashlib.sha256(code.upper().encode()).hexdigest()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @staticmethod
    async def initiate_totp_setup(
        db: AsyncSession, user_id: UUID, email: str
    ) -> Tuple[str, str, str, list[str]]:
        """
        Create an *unverified* MfaCredential.
        Returns (credential_id, totp_uri, secret, backup_codes).
        """
        secret = MfaService.generate_totp_secret()
        backup_codes = MfaService.generate_backup_codes()

        # Deactivate any previous unverified TOTP credentials
        old = await db.execute(
            select(MfaCredential).where(
                MfaCredential.user_id == user_id,
                MfaCredential.type == "totp",
                MfaCredential.is_verified == False,
            )
        )
        for cred in old.scalars().all():
            await db.delete(cred)

        cred = MfaCredential(
            user_id=user_id,
            type="totp",
            secret_encrypted=encrypt(secret),
            backup_codes_encrypted=encrypt_json(
                [MfaService._hash_backup_code(c) for c in backup_codes]
            ),
            is_verified=False,
            is_active=False,
        )
        db.add(cred)
        await db.commit()
        await db.refresh(cred)

        uri = MfaService.totp_uri(secret, email)
        return str(cred.id), uri, secret, backup_codes

    @staticmethod
    async def verify_and_activate_totp(
        db: AsyncSession, credential_id: UUID, code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify the setup code and activate the credential.
        Returns (success, error_message).
        """
        result = await db.execute(
            select(MfaCredential).where(MfaCredential.id == credential_id)
        )
        cred = result.scalar_one_or_none()
        if not cred:
            return False, "MFA credential not found"
        if cred.is_verified:
            return False, "Already verified"

        secret = decrypt(cred.secret_encrypted)
        totp = pyotp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            return False, "Invalid TOTP code"

        cred.is_verified = True
        cred.is_active = True

        # Enable MFA on the user account
        user_result = await db.execute(select(User).where(User.id == cred.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.mfa_enabled = True

        await db.commit()
        return True, None

    # ------------------------------------------------------------------
    # Verification (login time)
    # ------------------------------------------------------------------

    @staticmethod
    async def verify_totp_code(
        db: AsyncSession, user_id: UUID, code: str
    ) -> bool:
        """
        Verify a TOTP code or backup code at login time.
        Returns True if valid.
        """
        result = await db.execute(
            select(MfaCredential).where(
                MfaCredential.user_id == user_id,
                MfaCredential.type == "totp",
                MfaCredential.is_verified == True,
                MfaCredential.is_active == True,
            )
        )
        cred = result.scalar_one_or_none()
        if not cred:
            return False

        # Try TOTP first
        secret = decrypt(cred.secret_encrypted)
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            from datetime import datetime
            cred.last_used_at = datetime.utcnow()
            await db.commit()
            return True

        # Try backup codes
        code_hash = MfaService._hash_backup_code(code)
        try:
            backup_hashes: list[str] = decrypt_json(cred.backup_codes_encrypted)
        except Exception:
            return False

        if code_hash in backup_hashes:
            backup_hashes.remove(code_hash)
            cred.backup_codes_encrypted = encrypt_json(backup_hashes)
            from datetime import datetime
            cred.last_used_at = datetime.utcnow()
            await db.commit()
            return True

        return False

    # ------------------------------------------------------------------
    # Disable
    # ------------------------------------------------------------------

    @staticmethod
    async def disable_mfa(db: AsyncSession, user_id: UUID) -> bool:
        result = await db.execute(
            select(MfaCredential).where(MfaCredential.user_id == user_id)
        )
        for cred in result.scalars().all():
            await db.delete(cred)

        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.mfa_enabled = False

        await db.commit()
        return True

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    @staticmethod
    async def get_mfa_status(db: AsyncSession, user_id: UUID) -> dict:
        result = await db.execute(
            select(MfaCredential).where(
                MfaCredential.user_id == user_id,
                MfaCredential.is_active == True,
                MfaCredential.is_verified == True,
            )
        )
        cred = result.scalar_one_or_none()
        return {
            "enabled": cred is not None,
            "type": cred.type if cred else None,
            "last_used_at": cred.last_used_at if cred else None,
        }
