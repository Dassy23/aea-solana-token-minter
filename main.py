from aea.crypto.registries import crypto_registry, make_crypto, register_crypto


def main():
    supported = crypto_registry.supported_ids
    register_crypto(
        id_="solana", entry_point="aea_ledger_solana:SolanaCrypto")

    print(supported)


main()
