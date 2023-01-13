<!-- ABOUT THE PROJECT -->

## About The Project

The project is simple solana token minter. Creates a token mint if not already there and mints N tokens to owner wallet on an interval. Will be used as a sample for future AEAs.

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/Dassy23/aea-solana-token-minter.git
   ```
2. Install packages

   ```sh
   PIPENV_IGNORE_VIRTUALENVS=1 && pipenv --python 3.10 && pipenv shell
   git clone https://github.com/Dassy23/aea-ledger-solana.git
   cd aea-ledger-solana
   python setup.py install
   cd ..
   rm -rf aea-ledger-solana

   pip install open-aea['all']
   aea generate-key solana
   aea add-key solana
   aea get-address solana
   aea generate-wealth solana
   ```

3. run

```
aea run

```

<!-- USAGE EXAMPLES -->

## Usage

Config these parameters

- service_interval = time in seconds as to how frequently the mint is performed.
- mint_seed = seed used to create the mint pda
- mint_amount = amount to mint per interval

```
pipenv run agent
```

<!-- ROADMAP -->

## Roadmap

See the [open issues](https://github.com/8ball030/sushi-farmer/issues) for a list of proposed features (and known issues).
