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

"""This package contains a scaffold of a behaviour."""
from aea.skills.behaviours import TickerBehaviour

from typing import cast
from packages.dassy23.skills.spl_token_skill.dialogues import LedgerApiDialogues, ContractApiDialogues, ContractApiDialogue
from packages.dassy23.skills.spl_token_skill.strategy import Strategy
from aea_ledger_solana import PublicKey

from aea.configurations.base import PublicId
from packages.valory.protocols.ledger_api.message import LedgerApiMessage
from packages.valory.protocols.contract_api.message import ContractApiMessage
from aea.skills.base import Behaviour
from packages.valory.connections.ledger.connection import (
    PUBLIC_ID as LEDGER_CONNECTION_PUBLIC_ID,
)
LEDGER_API_ADDRESS = str(LEDGER_CONNECTION_PUBLIC_ID)


class TokenProgramBehaviour(TickerBehaviour):
    """This class scaffolds a behaviour."""

    def __init__(self, **kwargs):
        self.service_interval = kwargs.pop('service_interval')
        super(TokenProgramBehaviour, self).__init__(
            tick_interval=self.service_interval, **kwargs)

    def _create_mint_if_doesnt_exists(self):
        self.log(f"Querying contract to see if mint has already been created...")
        contract_api_dialogues = cast(
            ContractApiDialogues, self.context.contract_api_dialogues)
        strategy = cast(Strategy, self.context.strategy)

        contract_api_msg, contract_api_dialogue = contract_api_dialogues.create(
            counterparty=LEDGER_API_ADDRESS,
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            ledger_id="solana",
            contract_id="dassy23/spl_token_program:0.1.0",
            contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            callable="get_mint_info",
            kwargs=ContractApiMessage.Kwargs(
                {
                    "mint_address": PublicKey.create_with_seed(PublicKey(self.context.agent_address), strategy.mint_seed, PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")),
                }
            ),
        )

        self.context.outbox.put_message(message=contract_api_msg)

    def setup(self) -> None:
        """Implement the setup."""
        self.log = self.context.logger.info
        self.log(f"Token Minter started")

        # raise NotImplementedError

    def act(self) -> None:
        """Implement the act."""
        self.log = self.context.logger.info
        contract_api_dialogues = cast(
            ContractApiDialogues, self.context.contract_api_dialogues)
        strategy = cast(Strategy, self.context.strategy)
        mint_addresss = PublicKey.create_with_seed(PublicKey(self.context.agent_address), strategy.mint_seed, PublicKey(
            "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")).to_base58().decode()
        if strategy.mint_exists:
            contract_api_msg, contract_api_dialogue = contract_api_dialogues.create(
                counterparty=LEDGER_API_ADDRESS,
                performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,  # type: ignore
                ledger_id="solana",
                contract_id="dassy23/spl_token_program:0.1.0",
                contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                callable="mint_to",
                kwargs=ContractApiMessage.Kwargs(
                    {
                        "payer_address": self.context.agent_address,
                        "destination_owner_address": self.context.agent_address,
                        "authority_address": self.context.agent_address,
                        "mint_address": mint_addresss,
                        "amount": strategy.mint_amount,
                    }
                ),
            )
            contract_api_dialogue.terms = strategy.get_deploy_terms()

            self.context.outbox.put_message(message=contract_api_msg)
        else:
            self.log(f"Mint does not exist, creating it...")
            self._create_mint_if_doesnt_exists()

    def teardown(self) -> None:
        """Implement the task teardown."""
        # raise NotImplementedError
