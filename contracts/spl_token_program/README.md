# Solana SPL Token Program Contract

## Description

This contract package is used to interface with an SPL token program.

## Functions

- `get_balances(owner_address)`: Get token balances.
- `get_mint_info(mint_address)`: Get mint info.
- `get_ata_addresses(owner_address,mint_addresses)`: Get associated token addresses for a owner token account.
- `create_token_mint(payer_address, mint_addres,decimals,mint_authority,freeze_authority)`: Create a token mint.
- `create_ata(payer_address, owner_address,mint_address)`: Create an associated token account
- `mint_to(payer_address, owner_address)`: Get the transaction to mint `mint_quantity` number of a single

## Links

- <a href="https://spl.solana.com/token" target="_blank">SPL Token Standard</a>
