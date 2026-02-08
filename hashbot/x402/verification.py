"""x402 Payment signature verification."""

import json
from datetime import UTC, datetime

from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3

from hashbot.x402.payment import PaymentPayload, PaymentRequirements


class PaymentVerifier:
    """Verifies x402 payment signatures."""

    def __init__(self, web3: Web3, chain_id: int = 177):
        self.web3 = web3
        self.chain_id = chain_id

    def verify_signature(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
        expected_signer: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Verify a payment signature using EIP-712.

        Returns:
            Tuple of (is_valid, recovered_address)
        """
        try:
            # Parse the payload - it should contain signature and signed data
            payload_data = payload.payload
            if payload_data.startswith("0x"):
                payload_data = payload_data[2:]

            # Decode JSON payload containing signature and message
            try:
                decoded = json.loads(bytes.fromhex(payload_data).decode())
                signature = decoded.get("signature", "")
                signed_message = decoded.get("message", {})
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fallback: treat entire payload as signature
                signature = "0x" + payload_data if not payload_data.startswith("0x") else payload_data
                signed_message = None

            # Build EIP-712 typed data from requirements
            typed_data = self._build_typed_data(requirements, signed_message)

            # Recover signer from signature
            encoded = encode_typed_data(full_message=typed_data)
            recovered = Account.recover_message(encoded, signature=signature)

            # Verify signer if expected
            if expected_signer:
                is_valid = recovered.lower() == expected_signer.lower()
                return is_valid, recovered

            return True, recovered

        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False, None

    def _build_typed_data(
        self,
        requirements: PaymentRequirements,
        signed_message: dict | None = None,
    ) -> dict:
        """Build EIP-712 typed data structure."""
        deadline = 0
        if requirements.expires_at:
            deadline = int(requirements.expires_at.timestamp())

        message = signed_message or {
            "recipient": requirements.recipient,
            "amount": int(requirements.amount),
            "asset": requirements.asset,
            "nonce": requirements.nonce,
            "deadline": deadline,
        }

        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                ],
                "Payment": [
                    {"name": "recipient", "type": "address"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "asset", "type": "address"},
                    {"name": "nonce", "type": "string"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "primaryType": "Payment",
            "domain": {
                "name": "HashBot",
                "version": "1",
                "chainId": self.chain_id,
            },
            "message": message,
        }

    def verify_payment_params(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
    ) -> bool:
        """Verify payment parameters match requirements."""
        # Verify network matches
        if payload.network != requirements.network:
            return False

        # Verify nonce matches
        if payload.nonce != requirements.nonce:
            return False

        # Verify scheme matches
        if payload.scheme != requirements.scheme:
            return False

        return True


class EIP712Verifier:
    """EIP-712 typed data signature verification."""

    DOMAIN_TYPE = [
        {"name": "name", "type": "string"},
        {"name": "version", "type": "string"},
        {"name": "chainId", "type": "uint256"},
    ]

    PAYMENT_TYPE = [
        {"name": "recipient", "type": "address"},
        {"name": "amount", "type": "uint256"},
        {"name": "asset", "type": "address"},
        {"name": "nonce", "type": "string"},
        {"name": "deadline", "type": "uint256"},
    ]

    def __init__(self, chain_id: int, name: str = "HashBot", version: str = "1"):
        self.chain_id = chain_id
        self.name = name
        self.version = version

    def get_domain(self) -> dict:
        """Get EIP-712 domain."""
        return {
            "name": self.name,
            "version": self.version,
            "chainId": self.chain_id,
        }

    def get_typed_data(self, requirements: PaymentRequirements) -> dict:
        """Build EIP-712 typed data for signing."""
        return {
            "types": {
                "EIP712Domain": self.DOMAIN_TYPE,
                "Payment": self.PAYMENT_TYPE,
            },
            "primaryType": "Payment",
            "domain": self.get_domain(),
            "message": {
                "recipient": requirements.recipient,
                "amount": int(requirements.amount),
                "asset": requirements.asset,
                "nonce": requirements.nonce,
                "deadline": int(requirements.expires_at.timestamp())
                if requirements.expires_at
                else 0,
            },
        }

    def verify(
        self,
        typed_data: dict,
        signature: str,
        expected_signer: str,
    ) -> bool:
        """Verify EIP-712 signature."""
        try:
            # Recover signer from typed data signature
            # Note: web3.py doesn't have built-in EIP-712 support
            # Use eth_account for this
            from eth_account.messages import encode_typed_data

            encoded = encode_typed_data(full_message=typed_data)
            recovered = Account.recover_message(encoded, signature=signature)

            return recovered.lower() == expected_signer.lower()

        except Exception:
            return False
