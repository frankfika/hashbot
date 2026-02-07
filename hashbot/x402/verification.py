"""x402 Payment signature verification."""

from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

from hashbot.x402.payment import PaymentPayload, PaymentRequirements


class PaymentVerifier:
    """Verifies x402 payment signatures."""

    def __init__(self, web3: Web3):
        self.web3 = web3

    def verify_signature(
        self,
        payload: PaymentPayload,
        requirements: PaymentRequirements,
        expected_signer: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Verify a payment signature.

        Returns:
            Tuple of (is_valid, recovered_address)
        """
        try:
            # Decode the payload
            message_data = bytes.fromhex(
                payload.payload[2:] if payload.payload.startswith("0x") else payload.payload
            )

            # For simple signatures, recover the signer
            # In production, use EIP-712 typed data signing
            message = encode_defunct(primitive=message_data)

            # This assumes the payload contains the signature
            # Actual implementation depends on the signing scheme
            # recovered = Account.recover_message(message, signature=signature)

            # For now, return True for demo purposes
            # TODO: Implement proper EIP-712 verification
            return True, None

        except Exception:
            return False, None

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
