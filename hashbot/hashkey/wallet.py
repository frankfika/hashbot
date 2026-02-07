"""Wallet management for HashKey Chain."""

from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

from hashbot.hashkey.chain import HashKeyChain


class Wallet:
    """Wallet for signing and sending transactions."""

    def __init__(self, private_key: str, chain: HashKeyChain):
        """Initialize wallet with private key."""
        self.chain = chain
        self._account: LocalAccount = Account.from_key(private_key)

    @property
    def address(self) -> str:
        """Get wallet address."""
        return self._account.address

    @classmethod
    def create(cls, chain: HashKeyChain) -> "Wallet":
        """Create a new random wallet."""
        account = Account.create()
        return cls(account.key.hex(), chain)

    @classmethod
    def from_mnemonic(
        cls,
        mnemonic: str,
        chain: HashKeyChain,
        account_path: str = "m/44'/60'/0'/0/0",
    ) -> "Wallet":
        """Create wallet from mnemonic phrase."""
        Account.enable_unaudited_hdwallet_features()
        account = Account.from_mnemonic(mnemonic, account_path=account_path)
        return cls(account.key.hex(), chain)

    def get_balance(self) -> int:
        """Get native token balance in wei."""
        return self.chain.get_balance(self.address)

    def get_balance_ether(self) -> float:
        """Get native token balance in ether."""
        balance_wei = self.get_balance()
        return float(Web3.from_wei(balance_wei, "ether"))

    def sign_message(self, message: str | bytes) -> str:
        """Sign a message and return signature hex."""
        if isinstance(message, str):
            message = message.encode()

        from eth_account.messages import encode_defunct

        msg = encode_defunct(primitive=message)
        signed = self._account.sign_message(msg)
        return signed.signature.hex()

    def sign_typed_data(self, typed_data: dict[str, Any]) -> str:
        """Sign EIP-712 typed data."""
        from eth_account.messages import encode_typed_data

        encoded = encode_typed_data(full_message=typed_data)
        signed = self._account.sign_message(encoded)
        return signed.signature.hex()

    def sign_transaction(self, transaction: dict[str, Any]) -> bytes:
        """Sign a transaction and return raw signed tx."""
        # Ensure proper fields
        tx = {
            "chainId": self.chain.chain_id,
            "nonce": transaction.get(
                "nonce", self.chain.web3.eth.get_transaction_count(self.address)
            ),
            "gasPrice": transaction.get("gasPrice", self.chain.get_gas_price()),
            "gas": transaction.get("gas", 21000),
            "to": Web3.to_checksum_address(transaction["to"]),
            "value": transaction.get("value", 0),
            "data": transaction.get("data", b""),
        }

        signed = self._account.sign_transaction(tx)
        return signed.raw_transaction

    def send_transaction(
        self,
        to: str,
        value: int = 0,
        data: bytes = b"",
        gas: int | None = None,
        gas_price: int | None = None,
    ) -> str:
        """Send a transaction and return tx hash."""
        tx = {
            "to": to,
            "value": value,
            "data": data,
        }

        if gas:
            tx["gas"] = gas
        else:
            tx["gas"] = self.chain.estimate_gas(
                {"from": self.address, "to": to, "value": value, "data": data}
            )

        if gas_price:
            tx["gasPrice"] = gas_price

        signed_tx = self.sign_transaction(tx)
        return self.chain.send_raw_transaction(signed_tx)

    def send_native_token(
        self,
        to: str,
        amount_wei: int,
    ) -> str:
        """Send native token (HSK) to an address."""
        return self.send_transaction(to=to, value=amount_wei)

    async def send_transaction_async(
        self,
        to: str,
        value: int = 0,
        data: bytes = b"",
        gas: int | None = None,
        gas_price: int | None = None,
    ) -> str:
        """Send a transaction asynchronously."""
        tx = {
            "to": to,
            "value": value,
            "data": data,
            "gas": gas or 21000,
            "gasPrice": gas_price or await self.chain.get_gas_price_async(),
        }

        signed_tx = self.sign_transaction(tx)
        return await self.chain.send_raw_transaction_async(signed_tx)


class SigningService:
    """
    Secure signing service that keeps private keys separate from LLM.

    This follows x402 spec requirement:
    "Private keys MUST only be handled by trusted entities and
    never be handled directly by any LLM operating an agent."
    """

    def __init__(self, wallet: Wallet):
        self._wallet = wallet

    @property
    def address(self) -> str:
        """Get the signer address (public info only)."""
        return self._wallet.address

    async def sign_payment(
        self,
        recipient: str,
        amount: int,
        asset: str,
        nonce: str,
        deadline: int,
    ) -> str:
        """Sign a payment authorization."""
        typed_data = {
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
                "chainId": self._wallet.chain.chain_id,
            },
            "message": {
                "recipient": recipient,
                "amount": amount,
                "asset": asset,
                "nonce": nonce,
                "deadline": deadline,
            },
        }

        return self._wallet.sign_typed_data(typed_data)
