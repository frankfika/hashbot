"""Wallet service for user wallet management."""

import base64
import hashlib
import secrets
from decimal import Decimal
from typing import Any

from cryptography.fernet import Fernet
from eth_account import Account
from web3 import Web3

from hashbot.config import get_settings
from hashbot.db import crud
from hashbot.hashkey.chain import HashKeyChain
from hashbot.hashkey.tokens import ERC20Token


class WalletService:
    """Service for managing user wallets securely."""

    def __init__(self, chain: HashKeyChain | None = None):
        self.settings = get_settings()
        self.chain = chain or HashKeyChain(
            rpc_url=self.settings.hashkey_rpc_url,
            chain_id=self.settings.hashkey_chain_id,
        )
        self._hkdc_token: ERC20Token | None = None

    @property
    def hkdc_token(self) -> ERC20Token | None:
        """Get HKDC token instance."""
        if self._hkdc_token is None and self.settings.hkdc_contract_address:
            self._hkdc_token = ERC20Token(
                address=self.settings.hkdc_contract_address,
                chain=self.chain,
            )
        return self._hkdc_token

    def _get_encryption_key(self, user_id: int) -> bytes:
        """Derive encryption key from user ID and secret."""
        secret = self.settings.wallet_encryption_secret or "hashbot-default-secret"
        key_material = f"{secret}:{user_id}".encode()
        key_hash = hashlib.sha256(key_material).digest()
        return base64.urlsafe_b64encode(key_hash)

    def _encrypt_private_key(self, private_key: str, user_id: int) -> str:
        """Encrypt private key for storage."""
        key = self._get_encryption_key(user_id)
        fernet = Fernet(key)
        encrypted = fernet.encrypt(private_key.encode())
        return encrypted.decode()

    def _decrypt_private_key(self, encrypted_key: str, user_id: int) -> str:
        """Decrypt private key from storage."""
        key = self._get_encryption_key(user_id)
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_key.encode())
        return decrypted.decode()

    async def create_wallet(self, telegram_id: int, username: str | None = None) -> dict[str, Any]:
        """Create a new wallet for user."""
        # Get or create user
        user = await crud.get_or_create_user(
            telegram_id=telegram_id,
            username=username,
        )

        # Check if wallet already exists
        existing = await crud.get_user_wallet(user.id)
        if existing:
            return {
                "address": existing.address,
                "created": False,
                "message": "Wallet already exists",
            }

        # Generate new account
        account = Account.create()
        address = account.address
        private_key = account.key.hex()

        # Encrypt private key
        encrypted_key = self._encrypt_private_key(private_key, user.id)

        # Store wallet
        wallet = await crud.get_or_create_wallet(
            user_id=user.id,
            address=address,
            encrypted_key=encrypted_key,
        )

        return {
            "address": wallet.address,
            "created": True,
            "message": "Wallet created successfully",
            "warning": "Your wallet is secured. Keep your Telegram account safe!",
        }

    async def import_wallet(
        self,
        telegram_id: int,
        private_key: str,
        username: str | None = None,
    ) -> dict[str, Any]:
        """Import existing wallet from private key."""
        # Validate private key
        try:
            if not private_key.startswith("0x"):
                private_key = "0x" + private_key
            account = Account.from_key(private_key)
        except Exception:
            return {
                "success": False,
                "error": "Invalid private key format",
            }

        # Get or create user
        user = await crud.get_or_create_user(
            telegram_id=telegram_id,
            username=username,
        )

        # Check if wallet already exists
        existing = await crud.get_user_wallet(user.id)
        if existing:
            return {
                "success": False,
                "error": "Wallet already exists. Contact support to reset.",
            }

        # Encrypt and store
        encrypted_key = self._encrypt_private_key(private_key, user.id)
        wallet = await crud.get_or_create_wallet(
            user_id=user.id,
            address=account.address,
            encrypted_key=encrypted_key,
        )

        return {
            "success": True,
            "address": wallet.address,
            "message": "Wallet imported successfully",
        }

    async def get_wallet(self, telegram_id: int) -> dict[str, Any] | None:
        """Get wallet info for user."""
        wallet = await crud.get_wallet_by_telegram_id(telegram_id)
        if not wallet:
            return None

        return {
            "address": wallet.address,
            "user_id": wallet.user_id,
        }

    async def get_native_balance(self, address: str) -> Decimal:
        """Get native token (HSK) balance."""
        try:
            balance_wei = self.chain.get_balance(address)
            return Decimal(str(Web3.from_wei(balance_wei, "ether")))
        except Exception:
            return Decimal("0")

    async def get_hkdc_balance(self, address: str) -> Decimal:
        """Get HKDC token balance."""
        if not self.hkdc_token:
            return Decimal("0")
        try:
            return self.hkdc_token.balance_of_decimal(address)
        except Exception:
            return Decimal("0")

    async def get_balances(self, telegram_id: int) -> dict[str, Any] | None:
        """Get all balances for user."""
        wallet = await self.get_wallet(telegram_id)
        if not wallet:
            return None

        address = wallet["address"]
        native = await self.get_native_balance(address)
        hkdc = await self.get_hkdc_balance(address)

        return {
            "address": address,
            "hsk": native,
            "hkdc": hkdc,
        }

    async def send_hkdc(
        self,
        telegram_id: int,
        to_address: str,
        amount: Decimal,
    ) -> dict[str, Any]:
        """Send HKDC tokens."""
        # Get user and wallet
        user = await crud.get_user_by_telegram_id(telegram_id)
        if not user:
            return {"success": False, "error": "User not found"}

        wallet = await crud.get_user_wallet(user.id)
        if not wallet:
            return {"success": False, "error": "Wallet not found"}

        if not self.hkdc_token:
            return {"success": False, "error": "HKDC token not configured"}

        # Decrypt private key
        try:
            private_key = self._decrypt_private_key(
                wallet.encrypted_private_key, user.id
            )
        except Exception:
            return {"success": False, "error": "Failed to decrypt wallet"}

        # Create wallet instance
        from hashbot.hashkey.wallet import Wallet as ChainWallet
        chain_wallet = ChainWallet(private_key, self.chain)

        # Check balance
        balance = self.hkdc_token.balance_of_decimal(wallet.address)
        if balance < amount:
            return {
                "success": False,
                "error": f"Insufficient balance. Have {balance} HKDC, need {amount} HKDC",
            }

        # Convert to base units and send
        try:
            amount_base = self.hkdc_token.to_base_units(amount)
            tx_hash = self.hkdc_token.transfer(
                chain_wallet,
                Web3.to_checksum_address(to_address),
                amount_base,
            )

            # Wait for confirmation
            receipt = self.chain.wait_for_transaction(tx_hash, timeout=60)

            return {
                "success": receipt.get("status") == 1,
                "tx_hash": tx_hash,
                "explorer_url": self.chain.get_explorer_url(tx_hash),
                "amount": str(amount),
                "to": to_address,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_native(
        self,
        telegram_id: int,
        to_address: str,
        amount: Decimal,
    ) -> dict[str, Any]:
        """Send native HSK tokens."""
        # Get user and wallet
        user = await crud.get_user_by_telegram_id(telegram_id)
        if not user:
            return {"success": False, "error": "User not found"}

        wallet = await crud.get_user_wallet(user.id)
        if not wallet:
            return {"success": False, "error": "Wallet not found"}

        # Decrypt private key
        try:
            private_key = self._decrypt_private_key(
                wallet.encrypted_private_key, user.id
            )
        except Exception:
            return {"success": False, "error": "Failed to decrypt wallet"}

        # Create wallet instance
        from hashbot.hashkey.wallet import Wallet as ChainWallet
        chain_wallet = ChainWallet(private_key, self.chain)

        # Check balance
        balance = await self.get_native_balance(wallet.address)
        if balance < amount:
            return {
                "success": False,
                "error": f"Insufficient balance. Have {balance} HSK, need {amount} HSK",
            }

        # Send
        try:
            amount_wei = Web3.to_wei(amount, "ether")
            tx_hash = chain_wallet.send_native_token(
                Web3.to_checksum_address(to_address),
                amount_wei,
            )

            # Wait for confirmation
            receipt = self.chain.wait_for_transaction(tx_hash, timeout=60)

            return {
                "success": receipt.get("status") == 1,
                "tx_hash": tx_hash,
                "explorer_url": self.chain.get_explorer_url(tx_hash),
                "amount": str(amount),
                "to": to_address,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
