# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2022 dassy23
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

"""This module contains the scaffold contract definition."""

from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, cast
import logging
import json

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_solana import (SolanaCrypto, SolanaApi, SolanaFaucetApi,
                               PublicKey, Transaction, CreateAccountWithSeedParams, ssp, TransactionInstruction)
from spl.token.core import _TokenCore
from spl.token._layouts import ACCOUNT_LAYOUT, MINT_LAYOUT, MULTISIG_LAYOUT
import solana.system_program as sp
from solana.rpc import types
import spl.token.instructions as spl_token
from solders.transaction import Transaction as sTransaction


DEFAULT_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
DEFAULT_ATA_PROGRAM_ID = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"


_default_logger = logging.getLogger(
    "aea.packages.dassy23.contracts.spl_token_program.contract")


class TokenProgram(Contract):
    """The scaffold contract class for a smart contract."""

    contract_id = PublicId.from_str("dassy23/spl_token_program:0.1.0")

    @classmethod
    def get_dummy_val(
        cls, ledger_api: LedgerApi, contract_address: str,
        owner_address: str, **kwargs: Any
    ) -> JSONLike:
        """
        Get the balances for a specific owner address.

        Implement this method in the sub class if you want
        to handle the contract requests manually.


        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:
            return {"value": "dummy"}

    @classmethod
    def get_balances(
        cls, ledger_api: LedgerApi, contract_address,
        owner_address: str, **kwargs: Any
    ) -> JSONLike:
        """
        Get the balances for a specific owner address.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param owner: the wallet owner address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:

            opts = types.TokenAccountOpts(program_id=PublicKey(
                DEFAULT_TOKEN_PROGRAM_ID))
            response = ledger_api.api.get_token_accounts_by_owner_json_parsed(
                PublicKey(owner_address), opts=opts)
            balances = [{
                "mint": x.account.data.parsed['info']['mint'],
                "amount": x.account.data.parsed['info']['tokenAmount']['amount'],
                "decimals": x.account.data.parsed['info']['tokenAmount']['decimals']
            } for x in response.value]
            result = {
                x['mint']:
                    {
                        "amount": int(x['amount']),
                        "decimals": x['decimals']
                }
                for x in balances
            }
            return {"balances": result}

        raise NotImplementedError

    @classmethod
    def get_mint_info(
        cls,
        ledger_api: LedgerApi,
        contract_address: Optional[str],
        mint_address: str,
        **kwargs: Any
    ) -> JSONLike:
        """
        Get the info for a specific mint account.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param mint_address: the address of the mint.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:
            mint = ledger_api.api.get_account_info_json_parsed(
                PublicKey(mint_address))
            info = None if mint.value == None else mint.value.data.parsed['info']
            return {mint_address.to_base58().decode(): info}

        raise NotImplementedError

    @classmethod
    def get_ata_addresses(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        owner_address: str,
        mint_addresses: List[str],
        **kwargs: Any
    ) -> JSONLike:
        """
        Get the balances for a specific owner address.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param owner: the wallet owner address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:
            atas = {}
            for mint_address in mint_addresses:
                seeds = [
                    bytes(PublicKey(owner_address)),
                    bytes(PublicKey(contract_address)),
                    bytes(PublicKey(mint_address)),

                ]
                address = PublicKey.find_program_address(
                    seeds=seeds, program_id=PublicKey(DEFAULT_ATA_PROGRAM_ID))
                atas[mint_address] = (address[0].to_base58()).decode()
            return {"atas": atas}
        raise NotImplementedError

    @classmethod
    def create_token_mint(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        payer_address: str,
        mint_address: str,
        decimals: int,
        mint_authority: str,
        freeze_authority: str,
        seed: Optional[str] = "seed",
        **kwargs: Any
    ) -> JSONLike:
        """
        Create a token mint account.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis
        :param payer_address: the fee payer wallet address.
        :param mint_address: the mint wallet address.
        :param decimals: the number of decimals.
        :param mint_authority: the mint authority wallet address.
        :param freeze_authority: the freeze authority wallet address.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:

            resp = ledger_api.api.get_minimum_balance_for_rent_exemption(
                MINT_LAYOUT.sizeof())
            balance_needed = resp.value

            params = CreateAccountWithSeedParams(
                from_pubkey=PublicKey(payer_address),
                new_account_pubkey=PublicKey(mint_address),
                base_pubkey=PublicKey(payer_address),
                seed=seed,
                lamports=balance_needed,
                space=MINT_LAYOUT.sizeof(),
                program_id=PublicKey(contract_address)
            )

            createPDAInstruction = TransactionInstruction.from_solders(
                ssp.create_account_with_seed(params.to_solders()))

            txn = Transaction(fee_payer=PublicKey(payer_address))
            txn.add(
                createPDAInstruction
            )
            txn.add(
                spl_token.initialize_mint(
                    spl_token.InitializeMintParams(
                        program_id=PublicKey(contract_address),
                        mint=PublicKey(mint_address),
                        decimals=decimals,
                        mint_authority=PublicKey(mint_authority),
                        freeze_authority=PublicKey(freeze_authority),
                    )
                )
            )

            tx = txn._solders.to_json()
            return ledger_api.add_nonce(json.loads(tx))

        raise NotImplementedError

    @ classmethod
    def create_ata(
        cls,
        ledger_api: LedgerApi,
        contract_address: Optional[str],
        payer_address: str,
        owner_address: str,
        mint_address: str,
        **kwargs: Any
    ) -> JSONLike:
        """
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """

        if ledger_api.identifier == SolanaApi.identifier:

            txn = Transaction(fee_payer=PublicKey(payer_address))
            create_ata_txn = spl_token.create_associated_token_account(
                payer=PublicKey(payer_address), owner=PublicKey(owner_address), mint=PublicKey(mint_address)
            )
            txn.add(create_ata_txn)

            tx = txn._solders.to_json()
            return ledger_api.add_nonce(json.loads(tx))

        raise NotImplementedError

    @ classmethod
    def mint_to(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        payer_address: str,
        destination_owner_address: str,
        authority_address: str,
        mint_address: str,
        amount: int,
        ** kwargs: Any
    ) -> JSONLike:
        """
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """

        if ledger_api.identifier == SolanaApi.identifier:
            seeds = [
                bytes(PublicKey(destination_owner_address)),
                bytes(PublicKey(contract_address)),
                bytes(PublicKey(mint_address)),

            ]
            address_pk = PublicKey.find_program_address(
                seeds=seeds, program_id=PublicKey(DEFAULT_ATA_PROGRAM_ID))
            address = (address_pk[0].to_base58()).decode()
            sa = SolanaApi()
            ata = sa.get_state(address)
            if ata is None:
                txn = Transaction(fee_payer=PublicKey(payer_address))
                txn.add(
                    spl_token.create_associated_token_account(
                        payer=PublicKey(payer_address), owner=PublicKey(destination_owner_address), mint=PublicKey(mint_address)
                    ))
                txn.add(
                    spl_token.mint_to(
                        spl_token.MintToParams(
                            program_id=PublicKey(contract_address),
                            mint=PublicKey(mint_address),
                            dest=PublicKey(address),
                            mint_authority=PublicKey(authority_address),
                            amount=amount,
                        )
                    )
                )
                tx = txn._solders.to_json()
                return ledger_api.add_nonce(json.loads(tx))

            else:
                txn = Transaction(fee_payer=PublicKey(payer_address)).add(
                    spl_token.mint_to(
                        spl_token.MintToParams(
                            program_id=PublicKey(contract_address),
                            mint=PublicKey(mint_address),
                            dest=address_pk[0],
                            mint_authority=PublicKey(authority_address),
                            amount=amount
                        )
                    )
                )
                tx = txn._solders.to_json()
                return ledger_api.add_nonce(json.loads(tx))

        raise NotImplementedError

    @ classmethod
    def transfer_tokens(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        payer_address: str,
        sender_owner_address: str,
        destination_owner_address: str,
        mint_address: str,
        amount: int,
        ** kwargs: Any
    ) -> JSONLike:
        """
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:
            dest_seeds = [
                bytes(PublicKey(destination_owner_address)),
                bytes(PublicKey(contract_address)),
                bytes(PublicKey(mint_address)),

            ]
            address_pk = PublicKey.find_program_address(
                seeds=dest_seeds, program_id=PublicKey(DEFAULT_ATA_PROGRAM_ID))
            dest_address = (address_pk[0].to_base58()).decode()

            source_address = [
                bytes(PublicKey(sender_owner_address)),
                bytes(PublicKey(contract_address)),
                bytes(PublicKey(mint_address)),
            ]
            address_pk = PublicKey.find_program_address(
                seeds=source_address, program_id=PublicKey(DEFAULT_ATA_PROGRAM_ID))
            source_address = (address_pk[0].to_base58()).decode()

            sa = SolanaApi()
            ata = sa.get_state(dest_address)

            if ata is None:
                txn = Transaction(fee_payer=PublicKey(payer_address))
                txn.add(
                    spl_token.create_associated_token_account(
                        payer=PublicKey(payer_address), owner=PublicKey(destination_owner_address), mint=PublicKey(mint_address)
                    ))
                txn.add(
                    spl_token.transfer(
                        spl_token.TransferParams(
                            program_id=PublicKey(contract_address),
                            source=PublicKey(source_address),
                            dest=PublicKey(dest_address),
                            owner=PublicKey(sender_owner_address),
                            amount=amount
                        )
                    )
                )
            else:
                txn = Transaction(fee_payer=PublicKey(payer_address)).add(
                    spl_token.transfer(
                        spl_token.TransferParams(
                            program_id=PublicKey(contract_address),
                            source=PublicKey(source_address),
                            dest=PublicKey(dest_address),
                            owner=PublicKey(source_owner_address),
                            amount=amount
                        )
                    )
                )

            tx = txn._solders.to_json()
            return ledger_api.add_nonce(json.loads(tx))

        raise NotImplementedError

    @ classmethod
    def burn_tokens(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        payer_address: str,
        owner_address: str,
        mint_address: str,
        amount: int,
        ** kwargs: Any
    ) -> JSONLike:
        """
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:
            ata_seeds = [
                bytes(PublicKey(owner_address)),
                bytes(PublicKey(contract_address)),
                bytes(PublicKey(mint_address)),
            ]
            address_pk = PublicKey.find_program_address(
                seeds=ata_seeds, program_id=PublicKey(DEFAULT_ATA_PROGRAM_ID))
            source_address = (address_pk[0].to_base58()).decode()

            txn = Transaction(fee_payer=PublicKey(payer_address)).add(
                spl_token.burn(
                    spl_token.BurnParams(
                        program_id=PublicKey(contract_address),
                        account=PublicKey(source_address),
                        mint=PublicKey(mint_address),
                        owner=PublicKey(owner_address),
                        amount=amount
                    )
                )
            )

            tx = txn._solders.to_json()
            return ledger_api.add_nonce(json.loads(tx))
        raise NotImplementedError

    @ classmethod
    def close_ata(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        payer_address: str,
        owner_address: str,
        mint_address: str,
        destination_address: str,
        **kwargs: Any
    ) -> JSONLike:
        """
        "TOBEIMLEMENTED"
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        if ledger_api.identifier == SolanaApi.identifier:
            ata_seeds = [
                bytes(PublicKey(owner_address)),
                bytes(PublicKey(contract_address)),
                bytes(PublicKey(mint_address)),
            ]
            address_pk = PublicKey.find_program_address(
                seeds=ata_seeds, program_id=PublicKey(DEFAULT_ATA_PROGRAM_ID))
            ata = (address_pk[0].to_base58()).decode()

            txn = Transaction(fee_payer=PublicKey(payer_address)).add(
                spl_token.close_account(
                    spl_token.CloseAccountParams(
                        program_id=PublicKey(contract_address),
                        account=PublicKey(ata),
                        dest=PublicKey(destination_address),
                        owner=PublicKey(owner_address))
                )
            )
            tx = txn._solders.to_json()
            return ledger_api.add_nonce(json.loads(tx))

        raise NotImplementedError
