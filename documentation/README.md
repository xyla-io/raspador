# raspador

A Xyla scraper.

## Usage via Finder

Double click the `raspador.command` file.

## Usage via Terminal

Open the raspador root directory in Terminal and activate its environment.

```bash
cd PATH/TO/RASPADOR
source .venv/bin/activate
```

Raspador can then be run with:

```bash
python main.py <CONFIGURATION> <STARTDATE> <ENDDATE>
```

For example, to scrape COMPANY's data from October 1st through 31st:

```bash
python main.py COMPANY 2018-10-01 2018-10-31
```

You will need to log in AdWords site that Raspador launches in Firefox, then go back to the Terminal window and press `Return` to tell Raspador the window is ready to start scraping.

When the scrape is complete, Raspador will save a CSV file of the scraped data and prompt you to confirm that it should be uploaded.

If Raspador encounters any errors, it will ask you what to do, then try again automatically if you don't respond. If Raspador gets stuck with a page or data that it can't handle, you can try `Manual` mode, and Raspador will attempt to give you instructions in order to get it unstuck.

## Configuration

If a campaign has no data or is otherwise problematic, you may wish to remove it from the configuration file at `config/raspador_config.py` or add a modified local configuration file at `config/local_raspador_config.py` to override the defaul configuration. You can check out an example configuration file [local_raspador_config.py](_static/local_raspador_config.py)

## Credentials

Raspador can sign in automatically using credentials stored in a file at `credentials/local_raspador_credentials.py`.

You can download a template file [local_raspador_credentials.py](_static/local_raspador_credentials.py) and replace `IDENTITY`, `USER`, and `PASSWORD` with the appropriate credentials. You can add any number of `IDENTITY` blocks, and the `IDENTITY` values should correspond with the values of the `credentials` keys `raspador_configuration.py`.
