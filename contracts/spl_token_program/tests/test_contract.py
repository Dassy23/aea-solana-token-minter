# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2022 Valory AG
#   Copyright 2018-2020 Fetch.AI Limited
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""The tests module contains the tests of the packages/contracts/spl_token_program dir."""
# type: ignore # noqa: E800
# pylint: skip-file

import re
import time
from pathlib import Path
from typing import cast
from unittest import mock
from typing import Dict, Generator, Optional, Tuple, Union, cast
from aea.common import JSONLike


import pytest

from aea.configurations.loader import (
    ComponentType,
    ContractConfig,
    load_component_configuration,
)
from aea.contracts.base import Contract, contract_registry
from aea.test_tools.test_contract import BaseContractTestCase
from aea_ledger_solana import SolanaCrypto, SolanaApi, SolanaFaucetApi, PublicKey, Transaction, sTransaction
from spl.token._layouts import ACCOUNT_LAYOUT, MINT_LAYOUT, MULTISIG_LAYOUT


PACKAGE_DIR = Path(__file__).parent.parent
MAX_FLAKY_RERUNS = 3

DEFAULT_ADDRESS = "https://api.devnet.solana.com"


class TestContractCommon:
    """Other tests for the contract."""

    @classmethod
    def setup(cls) -> None:
        """Setup."""

        # Register smart contract used for testing
        cls.path_to_contract = PACKAGE_DIR

        # register contract
        configuration = cast(
            ContractConfig,
            load_component_configuration(
                ComponentType.CONTRACT, cls.path_to_contract),
        )
        configuration._directory = (  # pylint: disable=protected-access
            cls.path_to_contract
        )
        if str(configuration.public_id) not in contract_registry.specs:
            # load contract into sys modules
            Contract.from_config(configuration)
        cls.contract = contract_registry.make(str(configuration.public_id))

        CONFIG = {
            "address": DEFAULT_ADDRESS,
        }
        cls.ledger_api = SolanaApi(**CONFIG)
        cls.faucet = SolanaFaucetApi()

        # Create mock ledger with unknown identifier
        # cls.ledger_api = mock.Mock()
        # attrs = {"identifier": "dummy"}
        # cls.ledger_api.configure_mock(**attrs)

    @staticmethod
    def retry_airdrop_if_result_none(faucet, address, amount=None):
        cnt = 0
        tx = None
        while tx is None and cnt < 10:
            tx = faucet.get_wealth(address, amount, url=DEFAULT_ADDRESS)
            cnt += 1
            time.sleep(2)
        return tx

    def _generate_wealth_if_needed(self, api, address, amount=None) -> Union[str, None]:

        balance = api.get_balance(address)

        if balance >= 1000000000:
            return "not required"
        else:
            faucet = SolanaFaucetApi()
            cnt = 0
            transaction_digest = None
            while transaction_digest is None and cnt < 10:
                transaction_digest = faucet.get_wealth(address, amount)
                cnt += 1
                time.sleep(2)

            if transaction_digest == None:
                return "failed"
            else:
                transaction_receipt, is_settled = self._wait_get_receipt(
                    api, transaction_digest)
                if is_settled is True:
                    return "success"
                else:
                    return "failed"

    @staticmethod
    def _wait_get_receipt(solana_api: SolanaApi, transaction_digest: str) -> Tuple[Optional[JSONLike], bool]:
        transaction_receipt = None
        not_settled = True
        elapsed_time = 0
        time_to_wait = 40
        sleep_time = 0.25
        while not_settled and elapsed_time < time_to_wait:
            elapsed_time += sleep_time
            time.sleep(sleep_time)
            transaction_receipt = solana_api.get_transaction_receipt(
                transaction_digest)
            if transaction_receipt is None:
                continue
            is_settled = solana_api.is_transaction_settled(
                transaction_receipt)
            not_settled = not is_settled

        return transaction_receipt, not not_settled

    def _sign_and_settle(self, solana_api: SolanaApi, txn: dict, payer) -> [str, JSONLike]:
        txn = solana_api.add_nonce(txn)
        signed_transaction = payer.sign_transaction(
            txn)
        transaction_digest = solana_api.send_signed_transaction(
            signed_transaction)
        assert transaction_digest is not None
        transaction_receipt, is_settled = self._wait_get_receipt(
            self.ledger_api, transaction_digest)
        assert is_settled is True
        return [transaction_digest, transaction_receipt]

    @ pytest.mark.ledger
    def test_get_balances(self) -> None:
        """Test get token balances."""

        # Test if function is not implemented for unknown ledger
        balances = self.contract.get_balances(
            ledger_api=self.ledger_api,
            owner_address="B1csuSsnExBHZWpYSJNf4BHeSJn3hMN3tDJRWRHBfvGK"
        )
        assert "balances" in balances

    @pytest.mark.ledger
    def test_get_ata_addresses(self) -> None:

        addresses = self.contract.get_ata_addresses(
            ledger_api=self.ledger_api,
            owner_address="F1Xx2knK9233VLKouxAVeZRKygKqeLiLVhfY6RtRkHTj",
            mint_addresses=[
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "So11111111111111111111111111111111111111112"]
        )
        assert addresses['atas']["EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"] == "HtSwUNdUvZGzqNP8eWrv57Z6U3X6UztFEpVdszxwaTCw"
        assert addresses['atas']["So11111111111111111111111111111111111111112"] == "GtgntmHXSQ9dCbhuyXFESc3FwKnpWeTQszj2mRYzsvCH"

    @pytest.mark.ledger
    def test_create_token_mint(self) -> None:
        """Test if get_create_batch_transaction with wrong api identifier fails."""

        payer = SolanaCrypto("./solana_private_key.txt")
        resp = self._generate_wealth_if_needed(self.ledger_api, payer.address)
        assert resp != "failed", "Failed to generate wealth"

        receiver = SolanaCrypto()
        solana_api = SolanaApi()
        txn = solana_api.get_transfer_transaction(
            payer.address,
            receiver.address,
            1000000,
        )
        sig, tx = self._sign_and_settle(solana_api, txn, payer)

        seed = "seed"
        mint = PublicKey.create_with_seed(
            payer.public_key, seed, PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))

        amount = 23

        # # tx create mint
        # txn = self.contract.create_token_mint(
        #     ledger_api=self.ledger_api,
        #     contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        #     payer_address=payer.address,
        #     mint_address=mint.to_base58().decode(),
        #     decimals=6,
        #     mint_authority=payer.address,
        #     freeze_authority=payer.address,
        #     seed=seed
        # )
        # sig, tx = self._sign_and_settle(solana_api, txn, payer)

        # mint_info = self.contract.get_mint_info(
        #     ledger_api=self.ledger_api,
        #     contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        #     mint_address=mint.to_base58().decode(),
        # )
        # starting_state = self.ledger_api.get_state(mint.to_base58().decode())

        # # tx create ata for payer
        # txn = self.contract.create_ata(
        #     ledger_api=self.ledger_api,
        #     contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        #     payer_address=payer.address,
        #     owner_address=payer.address,
        #     mint_address=mint.to_base58().decode()
        # )
        # sig, tx = self._sign_and_settle(solana_api, txn, payer)

        state = self.ledger_api.get_state(mint.to_base58().decode())
        addresses = self.contract.get_ata_addresses(
            ledger_api=self.ledger_api,
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            owner_address=payer.address,
            mint_addresses=[mint.to_base58().decode()],
        )
        ata = addresses['atas'][mint.to_base58().decode()]

        # tx mint tokens to payer ata
        txn = self.contract.mint_to(
            ledger_api=self.ledger_api,
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            payer_address=payer.address,
            destination_owner_address=payer.address,
            mint_address=mint.to_base58().decode(),
            authority_address=payer.address,
            amount=amount
        )
        sig, tx = self._sign_and_settle(solana_api, txn, payer)

        ##

        transfer_amount = 5
        txn = self.contract.transfer_tokens(
            ledger_api=self.ledger_api,
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            payer_address=payer.address,
            sender_owner_address=payer.address,
            destination_owner_address=receiver.address,
            mint_address=mint.to_base58().decode(),
            amount=transfer_amount
        )

        sig, tx = self._sign_and_settle(solana_api, txn, payer)

        ##

        addresses = self.contract.get_ata_addresses(
            ledger_api=self.ledger_api,
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            owner_address=receiver.address,
            mint_addresses=[mint.to_base58().decode()],
        )
        receiver_ata = addresses['atas'][mint.to_base58().decode()]

        state = self.ledger_api.get_state(receiver_ata)
        balance = state.data.parsed['info']['tokenAmount']['amount']
        assert int(balance) >= transfer_amount

        # tx burn tokens
        burn_amount = transfer_amount
        txn = self.contract.burn_tokens(
            ledger_api=self.ledger_api,
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            payer_address=receiver.address,
            owner_address=receiver.address,
            mint_address=mint.to_base58().decode(),
            amount=burn_amount
        )

        sig, tx = self._sign_and_settle(solana_api, txn, receiver)

        ##

        # tx close ata
        txn = self.contract.close_ata(
            ledger_api=self.ledger_api,
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            payer_address=receiver.address,
            owner_address=receiver.address,
            mint_address=mint.to_base58().decode(),
            destination_address=payer.address
        )

        sig, tx = self._sign_and_settle(solana_api, txn, receiver)

        state = self.ledger_api.get_state(receiver_ata)

        assert state == None
        ##
