<!-- ABOUT THE PROJECT -->

## About The Project

The project is simple solana token minter. Creates a token mint if not already there and mints N tokens to owner wallet on an interval. Will be used as a sample for future AEAs.

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/Dassy23/aea-solana-token-minter.git
   ```
2. Install packages & write private key to file
   ```sh
   pip ins
   ```

<!-- USAGE EXAMPLES -->

## Usage

The auto harvester has a number of configurable parameters available in /skills/harvester/skill.yaml

Config these parameters

- service_interval = time in seconds as to how frequently the harvest is performed.
- min_sushi = minimum sushi after which to collect yield. (In gwei)

```
pipenv run agent
```

<!-- ROADMAP -->

## Roadmap

See the [open issues](https://github.com/8ball030/sushi-farmer/issues) for a list of proposed features (and known issues).
