# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 dassy23
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

"""This package contains a scaffold of a handler."""

from typing import Optional
from typing import cast

from aea.configurations.base import PublicId
from aea.protocols.base import Message
from aea.skills.base import Handler
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.protocols.ledger_api.message import LedgerApiMessage
from aea_ledger_solana import SolanaApi, PublicKey
from packages.dassy23.skills.spl_token_skill.dialogues import (
    LedgerApiDialogues,
    LedgerApiDialogue,
    ContractApiDialogue,
    ContractApiDialogues,
    SigningDialogues,
    SigningDialogue
)
from packages.dassy23.skills.spl_token_skill.strategy import Strategy

from packages.open_aea.protocols.signing.message import SigningMessage

from packages.valory.connections.ledger.connection import (
    PUBLIC_ID as LEDGER_CONNECTION_PUBLIC_ID,
)
from aea.crypto.ledger_apis import LedgerApis

LEDGER_API_ADDRESS = str(LEDGER_CONNECTION_PUBLIC_ID)


class TokenProgramHandler(Handler):
    """This class scaffolds a handler."""

    # type: Optional[PublicId]
    SUPPORTED_PROTOCOL = LedgerApiMessage.protocol_id

    def setup(self) -> None:
        """Implement the setup."""
        return

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to an envelope.
        :param message: the message
        """
        ledger_api_msg = cast(LedgerApiMessage, message)
        strategy = cast(Strategy, self.context.strategy)
        ledger_api_dialogues = cast(
            LedgerApiDialogues, self.context.ledger_api_dialogues
        )
        ledger_api_dialogue = cast(
            Optional[LedgerApiDialogue], ledger_api_dialogues.update(
                ledger_api_msg)
        )

        if ledger_api_msg.performative is LedgerApiMessage.Performative.BALANCE:
            if ledger_api_msg.balance != strategy.balance:
                strategy.balance = ledger_api_msg.balance
                self.context.logger.info(f"Balance is {strategy.balance}")
        elif ledger_api_msg.performative is LedgerApiMessage.Performative.TRANSACTION_DIGEST:
            self._handle_transaction_digest(
                ledger_api_msg, ledger_api_dialogue)
        elif (
            ledger_api_msg.performative
            is LedgerApiMessage.Performative.TRANSACTION_RECEIPT
        ):
            self._handle_transaction_receipt(
                ledger_api_msg, ledger_api_dialogue)
        else:
            self._handle_transaction_error(
                ledger_api_msg, ledger_api_dialogue)
            raise NotImplementedError

    def teardown(self) -> None:
        """Implement the handler teardown."""
        return

    def _handle_transaction_error(
        self, ledger_api_msg: LedgerApiMessage, ledger_api_dialogue: LedgerApiDialogue
    ) -> None:
        """
        Handle a message of transaction_digest performative.
        :param ledger_api_message: the ledger api message
        :param ledger_api_dialogue: the ledger api dialogue
        """
        self.context.logger.info(
            "transaction was successfully submitted. Transaction digest={}".format(
                ledger_api_msg.transaction_digest.body
            )
        )
        ledger_api_dialogues = cast(
            LedgerApiDialogues, self.context.ledger_api_dialogues
        )
        msg, ledger_api_dialogue = ledger_api_dialogues.create(
            counterparty=LEDGER_API_ADDRESS,
            performative=LedgerApiMessage.Performative.GET_TRANSACTION_RECEIPT,
            transaction_digest=ledger_api_msg.transaction_digest,
        )
        self.context.outbox.put_message(message=msg)
        self.context.logger.info("requesting transaction receipt.")

    def _handle_transaction_receipt(
        self, ledger_api_msg: LedgerApiMessage, ledger_api_dialogue: LedgerApiDialogue
    ) -> None:
        """
        Handle a message of transaction_receipt performative.
        :param ledger_api_message: the ledger api message
        """
        strategy = cast(Strategy, self.context.strategy)
        is_transaction_successful = LedgerApis.is_transaction_settled(
            ledger_api_msg.transaction_receipt.ledger_id,
            ledger_api_msg.transaction_receipt.receipt,
        )
        if is_transaction_successful:
            strategy.failed_txs = 0
        else:
            strategy.failed_txs += 1
        strategy.transacting = False
        self.context.logger.info(
            "transaction was successfully settled. post tx balances are : {}".format(
                [{"owner": x['owner'], "mint":x['mint'], "amount": x['uiTokenAmount']['uiAmountString']}
                    for x in ledger_api_msg.transaction_receipt.receipt['meta']['postTokenBalances']]
            )
        )

    def _handle_transaction_digest(
        self, ledger_api_msg: LedgerApiMessage, ledger_api_dialogue: LedgerApiDialogue
    ) -> None:
        """
        Handle a message of transaction_digest performative.
        :param ledger_api_message: the ledger api message
        :param ledger_api_dialogue: the ledger api dialogue
        """
        self.context.logger.info(
            "transaction was successfully submitted. Transaction digest={}".format(
                ledger_api_msg.transaction_digest.body
            )
        )
        ledger_api_dialogues = cast(
            LedgerApiDialogues, self.context.ledger_api_dialogues
        )
        msg, ledger_api_dialogue = ledger_api_dialogues.create(
            counterparty=LEDGER_API_ADDRESS,
            performative=LedgerApiMessage.Performative.GET_TRANSACTION_RECEIPT,
            transaction_digest=ledger_api_msg.transaction_digest,
        )
        self.context.outbox.put_message(message=msg)
        self.context.logger.info("requesting transaction receipt.")


class ContractApiHandler(Handler):
    """This class scaffolds a handler."""

    # type: Optional[PublicId]
    SUPPORTED_PROTOCOL = ContractApiMessage.protocol_id

    def setup(self) -> None:
        """Implement the setup."""

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to an envelope.

        :param message: the message
        """
        contract_api_msg = cast(ContractApiMessage, message)

        # recover dialogue
        contract_api_dialogues = cast(
            ContractApiDialogues, self.context.contract_api_dialogues
        )
        contract_api_dialogue = cast(
            Optional[ContractApiDialogue],
            contract_api_dialogues.update(contract_api_msg),
        )
        if contract_api_dialogue is None:
            self._handle_unidentified_dialogue(contract_api_msg)
            return

        # handle message
        if (
            contract_api_msg.performative
            is ContractApiMessage.Performative.RAW_TRANSACTION
        ):
            self._handle_raw_transaction(
                contract_api_msg, contract_api_dialogue)
        elif contract_api_msg.performative == ContractApiMessage.Performative.ERROR:
            self._handle_error(contract_api_msg, contract_api_dialogue)
        elif contract_api_msg.performative == ContractApiMessage.Performative.STATE:
            self._handle_state_update(contract_api_msg, contract_api_dialogue)
        else:
            self._handle_state_update(contract_api_msg, contract_api_dialogue)

    def teardown(self) -> None:
        """Implement the handler teardown."""
        # raise NotImplementedError

    def _handle_error(self, contract_api_msg, contract_api_dialogue):

        # state = contract_api_msg.state.body["result"]
        print("error_state")

    def _handle_state_update(self, contract_api_msg, contract_api_dialogue):
        self.log = self.context.logger.info
        strategy = cast(Strategy, self.context.strategy)
        state = contract_api_msg.state.body
        expected_mint = PublicKey.create_with_seed(PublicKey(
            self.context.agent_address), strategy.mint_seed, PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
        mint_address = expected_mint.to_base58().decode()

        mint = state.get(mint_address, None)

        if mint is not None:
            if mint['mintAuthority'] == self.context.agent_address:
                self.log(
                    f"Mint: {mint_address} exists with : {mint['supply']} supply")
                strategy.mint_exists = True
            else:
                raise ValueError()(
                    "Mint authority is not the agent address, try using a different seed to create mint")
        else:
            contract_api_dialogues = cast(
                ContractApiDialogues, self.context.contract_api_dialogues)
            strategy = cast(Strategy, self.context.strategy)

            contract_api_msg, contract_api_dialogue = contract_api_dialogues.create(
                counterparty=LEDGER_API_ADDRESS,
                performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,  # type: ignore
                ledger_id="solana",
                contract_id="dassy23/spl_token_program:0.1.0",
                contract_address="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                callable="create_token_mint",
                kwargs=ContractApiMessage.Kwargs(
                    {
                        "payer_address": self.context.agent_address,
                        "mint_address": mint_address,
                        "decimals": 0,
                        "mint_authority": self.context.agent_address,
                        "freeze_authority": self.context.agent_address,
                        "seed": strategy.mint_seed,
                    }
                ),
            )
            contract_api_dialogue.terms = strategy.get_deploy_terms()

            self.context.outbox.put_message(message=contract_api_msg)

    def _handle_raw_transaction(self, contract_api_msg, contract_api_dialogue):

        signing_dialogues = cast(
            SigningDialogues, self.context.signing_dialogues)
        signing_msg, signing_dialogue = signing_dialogues.create(
            counterparty=self.context.decision_maker_address,
            performative=SigningMessage.Performative.SIGN_TRANSACTION,
            raw_transaction=contract_api_msg.raw_transaction,
            terms=contract_api_dialogue.terms,

        )

        signing_dialogue = cast(SigningDialogue, signing_dialogue)
        signing_dialogue.associated_contract_api_dialogue = contract_api_dialogue
        self.context.decision_maker_message_queue.put_nowait(signing_msg)
        self.context.logger.info(
            "proposing the transaction to the decision maker. Waiting for confirmation ..."
        )


class SigningHandler(Handler):
    """Implement the transaction handler."""

    SUPPORTED_PROTOCOL = SigningMessage.protocol_id

    def setup(self) -> None:
        """Implement the setup for the handler."""
        pass

    def handle(self, message: Message) -> None:
        """
        Implement the reaction to a message.
        :param message: the message
        :return: None
        """
        signing_msg = cast(SigningMessage, message)

        # recover dialogue
        signing_dialogues = cast(
            SigningDialogues, self.context.signing_dialogues)
        signing_dialogue = cast(
            Optional[SigningDialogue], signing_dialogues.update(signing_msg)
        )
        if signing_dialogue is None:
            self._handle_unidentified_dialogue(signing_msg)
            return

        # handle message
        if signing_msg.performative is SigningMessage.Performative.SIGNED_TRANSACTION:
            self._handle_signed_transaction(signing_msg, signing_dialogue)
        elif signing_msg.performative is SigningMessage.Performative.ERROR:
            self._handle_error(signing_msg, signing_dialogue)
        else:
            self._handle_invalid(signing_msg, signing_dialogue)

    def teardown(self) -> None:
        """
        Implement the handler teardown.
        :return: None
        """
        pass

    def _handle_signed_transaction(
        self, signing_msg: SigningMessage, signing_dialogue: SigningDialogue
    ) -> None:
        """
        Handle an oef search message.
        :param signing_msg: the signing message
        :param signing_dialogue: the dialogue
        :return: None
        """
        self.context.logger.info("transaction signing was successful.")
        ledger_api_dialogues = cast(
            LedgerApiDialogues, self.context.ledger_api_dialogues
        )
        ledger_api_msg, ledger_api_dialogue = ledger_api_dialogues.create(
            counterparty=LEDGER_API_ADDRESS,
            performative=LedgerApiMessage.Performative.SEND_SIGNED_TRANSACTION,
            signed_transaction=signing_msg.signed_transaction,
        )
        ledger_api_dialogue = cast(LedgerApiDialogue, ledger_api_dialogue)
        ledger_api_dialogue.associated_signing_dialogue = signing_dialogue
        self.context.outbox.put_message(message=ledger_api_msg)
        self.context.logger.info("sending transaction to ledger.")
