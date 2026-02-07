"""ERC20 token interactions for HashKey Chain."""

from decimal import Decimal
from typing import Any

from web3 import Web3

from hashbot.hashkey.chain import HashKeyChain
from hashbot.hashkey.wallet import Wallet

# Standard ERC20 ABI (minimal)
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "name",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_from", "type": "address"},
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transferFrom",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]


class ERC20Token:
    """ERC20 token interaction wrapper."""

    def __init__(
        self,
        address: str,
        chain: HashKeyChain,
        abi: list[dict[str, Any]] | None = None,
    ):
        self.address = Web3.to_checksum_address(address)
        self.chain = chain
        self._contract = chain.web3.eth.contract(
            address=self.address,
            abi=abi or ERC20_ABI,
        )
        self._decimals: int | None = None
        self._symbol: str | None = None
        self._name: str | None = None

    @property
    def decimals(self) -> int:
        """Get token decimals."""
        if self._decimals is None:
            self._decimals = self._contract.functions.decimals().call()
        return self._decimals

    @property
    def symbol(self) -> str:
        """Get token symbol."""
        if self._symbol is None:
            self._symbol = self._contract.functions.symbol().call()
        return self._symbol

    @property
    def name(self) -> str:
        """Get token name."""
        if self._name is None:
            self._name = self._contract.functions.name().call()
        return self._name

    def balance_of(self, address: str) -> int:
        """Get token balance in base units."""
        return self._contract.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()

    def balance_of_decimal(self, address: str) -> Decimal:
        """Get token balance as decimal."""
        balance = self.balance_of(address)
        return Decimal(balance) / Decimal(10**self.decimals)

    def allowance(self, owner: str, spender: str) -> int:
        """Get allowance for spender."""
        return self._contract.functions.allowance(
            Web3.to_checksum_address(owner),
            Web3.to_checksum_address(spender),
        ).call()

    def build_transfer(
        self,
        to: str,
        amount: int,
    ) -> dict[str, Any]:
        """Build transfer transaction data."""
        return self._contract.functions.transfer(
            Web3.to_checksum_address(to),
            amount,
        ).build_transaction(
            {
                "gas": 100000,
                "gasPrice": self.chain.get_gas_price(),
            }
        )

    def build_approve(
        self,
        spender: str,
        amount: int,
    ) -> dict[str, Any]:
        """Build approve transaction data."""
        return self._contract.functions.approve(
            Web3.to_checksum_address(spender),
            amount,
        ).build_transaction(
            {
                "gas": 60000,
                "gasPrice": self.chain.get_gas_price(),
            }
        )

    def transfer(
        self,
        wallet: Wallet,
        to: str,
        amount: int,
    ) -> str:
        """Transfer tokens and return tx hash."""
        tx_data = self.build_transfer(to, amount)
        tx_data["from"] = wallet.address
        tx_data["nonce"] = self.chain.web3.eth.get_transaction_count(wallet.address)

        signed_tx = wallet.sign_transaction(tx_data)
        return self.chain.send_raw_transaction(signed_tx)

    def approve(
        self,
        wallet: Wallet,
        spender: str,
        amount: int,
    ) -> str:
        """Approve spender and return tx hash."""
        tx_data = self.build_approve(spender, amount)
        tx_data["from"] = wallet.address
        tx_data["nonce"] = self.chain.web3.eth.get_transaction_count(wallet.address)

        signed_tx = wallet.sign_transaction(tx_data)
        return self.chain.send_raw_transaction(signed_tx)

    def to_base_units(self, amount: Decimal | float | str) -> int:
        """Convert decimal amount to base units."""
        return int(Decimal(str(amount)) * Decimal(10**self.decimals))

    def from_base_units(self, amount: int) -> Decimal:
        """Convert base units to decimal amount."""
        return Decimal(amount) / Decimal(10**self.decimals)


class HKDC(ERC20Token):
    """
    HKDC - Hong Kong Dollar Stablecoin on HashKey Chain.

    Note: Contract address should be set via configuration.
    This is a placeholder implementation.
    """

    def __init__(self, address: str, chain: HashKeyChain):
        super().__init__(address, chain)
        # Override cached values for known token
        self._decimals = 18
        self._symbol = "HKDC"
        self._name = "Hong Kong Dollar Coin"


class PaymentSettler:
    """Settle payments on-chain."""

    def __init__(self, token: ERC20Token, wallet: Wallet):
        self.token = token
        self.wallet = wallet

    def settle_payment(
        self,
        from_address: str,
        to_address: str,
        amount: int,
    ) -> dict[str, Any]:
        """
        Settle a payment by transferring tokens.

        In a real implementation, this would:
        1. Verify the signed payment authorization
        2. Use transferFrom if approved
        3. Or use a payment channel contract
        """
        # For direct transfers (when this wallet holds funds)
        tx_hash = self.token.transfer(
            self.wallet,
            to_address,
            amount,
        )

        receipt = self.token.chain.wait_for_transaction(tx_hash)

        return {
            "success": receipt.get("status") == 1,
            "transaction_hash": tx_hash,
            "block_number": receipt.get("blockNumber"),
            "gas_used": receipt.get("gasUsed"),
        }
