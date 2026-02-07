"""HashKey Chain interaction layer."""

from typing import Any

from web3 import AsyncWeb3, Web3
from web3.middleware import ExtraDataToPOAMiddleware


class HashKeyChain:
    """HashKey Chain connection and utilities."""

    # Network configurations
    NETWORKS = {
        "mainnet": {
            "rpc_url": "https://mainnet.hashkeychain.io",
            "chain_id": 133,
            "explorer": "https://explorer.hashkeychain.io",
            "name": "HashKey Chain Mainnet",
        },
        "testnet": {
            "rpc_url": "https://hashkeychain-testnet.alt.technology",
            "chain_id": 177,
            "explorer": "https://hashkeychain-testnet-explorer.alt.technology",
            "name": "HashKey Chain Testnet",
        },
    }

    def __init__(
        self,
        rpc_url: str | None = None,
        chain_id: int | None = None,
        network: str = "testnet",
    ):
        """Initialize HashKey Chain connection."""
        if rpc_url and chain_id:
            self.rpc_url = rpc_url
            self.chain_id = chain_id
            self.network_name = "custom"
        else:
            config = self.NETWORKS.get(network, self.NETWORKS["testnet"])
            self.rpc_url = config["rpc_url"]
            self.chain_id = config["chain_id"]
            self.network_name = config["name"]

        self._web3: Web3 | None = None
        self._async_web3: AsyncWeb3 | None = None

    @property
    def web3(self) -> Web3:
        """Get synchronous Web3 instance."""
        if self._web3 is None:
            self._web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            # Add POA middleware for HashKey Chain
            self._web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        return self._web3

    @property
    def async_web3(self) -> AsyncWeb3:
        """Get async Web3 instance."""
        if self._async_web3 is None:
            self._async_web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.rpc_url))
        return self._async_web3

    def is_connected(self) -> bool:
        """Check if connected to the network."""
        try:
            return self.web3.is_connected()
        except Exception:
            return False

    async def is_connected_async(self) -> bool:
        """Check if connected (async)."""
        try:
            return await self.async_web3.is_connected()
        except Exception:
            return False

    def get_balance(self, address: str) -> int:
        """Get native token balance in wei."""
        return self.web3.eth.get_balance(Web3.to_checksum_address(address))

    async def get_balance_async(self, address: str) -> int:
        """Get native token balance in wei (async)."""
        return await self.async_web3.eth.get_balance(Web3.to_checksum_address(address))

    def get_block_number(self) -> int:
        """Get current block number."""
        return self.web3.eth.block_number

    async def get_block_number_async(self) -> int:
        """Get current block number (async)."""
        return await self.async_web3.eth.block_number

    def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Get transaction by hash."""
        return dict(self.web3.eth.get_transaction(tx_hash))

    async def get_transaction_async(self, tx_hash: str) -> dict[str, Any]:
        """Get transaction by hash (async)."""
        return dict(await self.async_web3.eth.get_transaction(tx_hash))

    def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None:
        """Get transaction receipt."""
        receipt = self.web3.eth.get_transaction_receipt(tx_hash)
        return dict(receipt) if receipt else None

    async def get_transaction_receipt_async(self, tx_hash: str) -> dict[str, Any] | None:
        """Get transaction receipt (async)."""
        receipt = await self.async_web3.eth.get_transaction_receipt(tx_hash)
        return dict(receipt) if receipt else None

    def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> dict[str, Any]:
        """Wait for transaction confirmation."""
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        return dict(receipt)

    def send_raw_transaction(self, signed_tx: bytes) -> str:
        """Send a signed transaction."""
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx)
        return tx_hash.hex()

    async def send_raw_transaction_async(self, signed_tx: bytes) -> str:
        """Send a signed transaction (async)."""
        tx_hash = await self.async_web3.eth.send_raw_transaction(signed_tx)
        return tx_hash.hex()

    def get_gas_price(self) -> int:
        """Get current gas price."""
        return self.web3.eth.gas_price

    async def get_gas_price_async(self) -> int:
        """Get current gas price (async)."""
        return await self.async_web3.eth.gas_price

    def estimate_gas(self, transaction: dict[str, Any]) -> int:
        """Estimate gas for a transaction."""
        return self.web3.eth.estimate_gas(transaction)

    def get_explorer_url(self, tx_hash: str) -> str:
        """Get block explorer URL for a transaction."""
        explorer = self.NETWORKS.get(
            "mainnet" if self.chain_id == 133 else "testnet", {}
        ).get("explorer", "")
        return f"{explorer}/tx/{tx_hash}" if explorer else ""
