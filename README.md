# Web to Image - Delta Chat Bot

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A Delta Chat bot that allows saving website URLs as images (taking screenshots of websites)

## Install

```sh
pip install web2img-deltabot
```

Then, to setup [Playwright](https://playwright.dev/python/docs/intro), run:

```sh
playwright install
```

## Usage

To configure the bot:

```sh
web2img-bot init bot@example.org SuperHardPassword
```

To customize the bot name, avatar and status/signature:

```sh
web2img-bot set_avatar /path/to/avatar.png
web2img-bot config displayname "Web to Image"
web2img-bot config selfstatus "Hi, send me some URL to convert it to image"
```

Finally you can start the bot with:

```sh
web2img-bot
```

To see the available options, run in the command line:

```
web2img-bot --help
```

**Note:** You can also run the bot CLI with `python -m web2img-deltabot`
