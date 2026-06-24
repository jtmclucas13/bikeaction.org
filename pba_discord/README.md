# About

This directory contains the code that sets up our Discord integration.

## Local development

This guide walks you through how to create a private Discord server with a Discord bot linked to a local implementation that can be used for testing.

The [interactions.py](https://interactions-py.github.io/interactions.py/Guides/02%20Creating%20Your%20Bot/) setup documentation does a pretty good job of walking through how to create a bot and invite it to a Discord server. If you run into issues with the below instructions, check there for updated instructions.

### Create an Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
1. Click "New Application".
1. Give your app a name.
1. Go to the "Installation" tab.
1. Set "Install Link" to "None". This is required to make your bot private.
1. Go to the "OAuth2" tab.
1. In your local `.env` file, set `DISCORD_OAUTH_CLIENT_ID` to the Client ID and `DISCORD_OAUTH_CLIENT_SECRET` to the Client Secret (you may need to click "Reset Secret"to view it). You will need to restart your local environment to set these environment variables inside the app container.
1. Under "Redirects", add `http://localhost:8000/accounts/discord/login/callback/`.

### Create a Bot

1. Go to the Bot tab of the Application you just created/
1. Click "Add Bot".
1. Click "Reset Token". Make sure to grab/save the new token value, you'll need it at the end. You can always reset it later if you need, since this is just for testing.
1. Uncheck "Public Bot", only you should be able to install your own bot.
1. Check all of the options under "Privileged Gateway Intents", you need these to receive events and message content.

### Create a server

1. Inside of Discord, click "Add a server", then "Create My Own".
1. You can customize it however you want, no option really matters here.

### Invite your bot to the server

1. Go to the OAuth2 tab of the Application you previously created.
1. Under "OAuth2 URL Generator", check `bot` and `applications.commands`.
1. Select "Guild Install" for "Integration Type".
1. Copy the URL that was generated.
1. Paste that URL into any channel on the server you created.
1. Navigate to that URL, complete the OAuth flow to invite your bot.

### Instantiate the local bot

1. In your local `.env` file, set `DISCORD_BOT_TOKEN` to the bot token that you grabbed earlier.
1. Run `docker compose up discord` to restart the Docker container that runs the bot, this time with your token.

The bot should now be able to use commands, listen to messages, and interact with local Django admin! Test it by running `/neighborhood` in your server, then going to Django admin and finding the request in the Neighborhoods page.

You can also now connect profiles to Discord accounts with an OAuth connection to your test app.
