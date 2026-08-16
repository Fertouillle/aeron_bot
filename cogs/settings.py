import discord
import json
import os
import traceback
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────
#  OWNER ONLY
# ─────────────────────────────────────────

OWNER_ID = 219821139910852619

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_WARN    = 0xB8860B
COLOR_DANGER  = 0x8B1A1A

CONFIG_FILE = "config.json"

TICKETS_LABELS = {
    "aide":        "❓ Aide / Question",
    "deban":       "🔓 Demande de déban",
    "plainte":     "⚠️ Plainte",
    "recrutement": "📋 Recrutement",
    "partenariat": "🤝 Partenariat",
    "bug":         "🐛 Bug",
}

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"tickets": {"logs_channel_id": None, "roles": {k: [] for k in TICKETS_LABELS}}}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────
#  VUE : MENU PRINCIPAL
# ─────────────────────────────────────────

class SettingsMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Bienvenue", emoji="👋", style=discord.ButtonStyle.primary)
    async def welcome_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config     = load_config()
        channel_id = config.get("welcome", {}).get("channel_id")
        current    = f"<#{channel_id}>" if channel_id else "*Non configuré*"

        embed = discord.Embed(
            title="◈  SETTINGS — BIENVENUE  ◈",
            description=f"**Salon actuel :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsWelcomeView())

    @discord.ui.button(label="Règlement", emoji="📜", style=discord.ButtonStyle.primary)
    async def reglement_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config  = load_config()
        role_id = config.get("reglement", {}).get("role_id")
        current = f"<@&{role_id}>" if role_id else "*Non configuré*"

        embed = discord.Embed(
            title="◈  SETTINGS — RÈGLEMENT  ◈",
            description=f"**Rôle attribué à l'acceptation :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsReglementView())

    @discord.ui.button(label="Système de tickets", emoji="🎫", style=discord.ButtonStyle.primary)
    async def tickets_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS — TICKETS  ◈",
            description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())

    @discord.ui.button(label="Sondages", emoji="🗳️", style=discord.ButtonStyle.primary)
    async def sondage_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config     = load_config()
        channel_id = config.get("sondage", {}).get("logs_channel_id")
        current    = f"<#{channel_id}>" if channel_id else "*Non configuré*"

        embed = discord.Embed(
            title="◈  SETTINGS — SONDAGES  ◈",
            description=f"**Salon de logs actuel :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsSondageView())

    @discord.ui.button(label="Modération", emoji="🔨", style=discord.ButtonStyle.primary)
    async def moderation_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config     = load_config()
        channel_id = config.get("moderation", {}).get("logs_channel_id")
        current    = f"<#{channel_id}>" if channel_id else "*Non configuré*"

        embed = discord.Embed(
            title="◈  SETTINGS — MODÉRATION  ◈",
            description=f"**Salon de logs actuel :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationView())

    @discord.ui.button(label="Captcha", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def captcha_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config  = load_config()
        captcha = config.get("captcha", {})
        enabled            = captcha.get("enabled", False)
        verified_role_id   = captcha.get("verified_role_id")
        unverified_role_id = captcha.get("unverified_role_id")
        verif_channel_id   = captcha.get("verification_channel_id")
        logs_channel_id    = captcha.get("logs_channel_id")
        embed = discord.Embed(
            title="◈  SETTINGS — CAPTCHA  ◈",
            description=(
                f"**Statut :** {'✅ Activé' if enabled else '❌ Désactivé'}\n"
                f"**Salon de vérification :** {f'<#{verif_channel_id}>' if verif_channel_id else '*Non configuré*'}\n"
                f"**Salon de logs :** {f'<#{logs_channel_id}>' if logs_channel_id else '*Non configuré*'}\n"
                f"**Rôle Non vérifié :** {f'<@&{unverified_role_id}>' if unverified_role_id else '*Non configuré*'}\n"
                f"**Rôle Vérifié :** {f'<@&{verified_role_id}>' if verified_role_id else '*Non configuré*'}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())

    @discord.ui.button(label="Salons vocaux", emoji="🔊", style=discord.ButtonStyle.primary)
    async def vocal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        config     = load_config()
        channel_id = config.get("vocal", {}).get("hub_channel_id")
        current    = f"<#{channel_id}>" if channel_id else "*Non configuré*"

        embed = discord.Embed(
            title="◈  SETTINGS — SALONS VOCAUX  ◈",
            description=(
                f"**Salon \"Créer votre salon\" actuel :** {current}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsVocalView())

    @discord.ui.button(label="Rôles à réaction", emoji="🎭", style=discord.ButtonStyle.primary)
    async def reaction_roles_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.reactionroles import ReactionRolesMenuView

        embed = discord.Embed(
            title="◈  SETTINGS — RÔLES À RÉACTION  ◈",
            description=(
                "Crée un panneau de rôles ou modifie un panneau existant.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "➕ **Créer un panneau** — Choisis un titre, une description et un salon\n"
                "🛠️ **Gérer un panneau existant** — Ajoute/retire des rôles sans tout refaire"
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=ReactionRolesMenuView())

    @discord.ui.button(label="Anti-abus", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def automod_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.automod import get_automod_config, AutomodSettingsView, build_automod_embed

        automod = get_automod_config()
        embed = build_automod_embed(automod)
        await interaction.response.edit_message(embed=embed, view=AutomodSettingsView())

    @discord.ui.button(label="Statut serveur GMod", emoji="🎮", style=discord.ButtonStyle.primary)
    async def gmod_status_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.gmod_status import get_gmod_status_config, build_gmod_settings_embed, GmodStatusSettingsView

        cfg = get_gmod_status_config()
        await interaction.response.edit_message(embed=build_gmod_settings_embed(cfg), view=GmodStatusSettingsView())

    @discord.ui.button(label="Contrôle serveur (RCON)", emoji="🕹️", style=discord.ButtonStyle.primary)
    async def rcon_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.rcon import build_rcon_menu_embed, RconMenuView

        await interaction.response.edit_message(embed=build_rcon_menu_embed(), view=RconMenuView())

    @discord.ui.button(label="Niveaux / XP", emoji="🏅", style=discord.ButtonStyle.primary)
    async def levels_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.levels import get_levels_config, build_levels_settings_embed, LevelsSettingsView

        cfg = get_levels_config()
        await interaction.response.edit_message(embed=build_levels_settings_embed(cfg), view=LevelsSettingsView())

    @discord.ui.button(label="Anniversaires", emoji="🎂", style=discord.ButtonStyle.primary)
    async def birthdays_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.birthdays import get_birthdays_config, build_birthdays_settings_embed, BirthdaysSettingsView

        cfg = get_birthdays_config()
        await interaction.response.edit_message(embed=build_birthdays_settings_embed(cfg), view=BirthdaysSettingsView())

# ─────────────────────────────────────────
#  VUE : BIENVENUE
# ─────────────────────────────────────────

class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon de bienvenue...",
            channel_types=[discord.ChannelType.text],
            custom_id="welcome_channel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            config  = load_config()
            if "welcome" not in config:
                config["welcome"] = {}
            config["welcome"]["channel_id"] = channel.id
            save_config(config)

            embed = discord.Embed(
                title="◈  BIENVENUE CONFIGURÉ  ◈",
                description=f"✅ Les messages de bienvenue seront envoyés dans {channel.mention}.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsWelcomeView())
        except Exception as e:
            print(f"❌ ERREUR WELCOME : {e}")
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class SettingsWelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(WelcomeChannelSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())

# ─────────────────────────────────────────
#  VUE : RÈGLEMENT
# ─────────────────────────────────────────

class ReglementRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le rôle à attribuer...",
            custom_id="reglement_role_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            role   = self.values[0]
            config = load_config()
            if "reglement" not in config:
                config["reglement"] = {}
            config["reglement"]["role_id"] = role.id
            save_config(config)

            embed = discord.Embed(
                title="◈  RÈGLEMENT CONFIGURÉ  ◈",
                description=f"✅ Le rôle {role.mention} sera attribué à l'acceptation du règlement.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsReglementView())
        except Exception as e:
            print(f"❌ ERREUR RÈGLEMENT : {e}")
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class ReglementChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon...",
            channel_types=[discord.ChannelType.text],
            custom_id="reglement_channel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            from cogs.reglement import build_reglement_embeds, ReglementView

            channel = interaction.guild.get_channel(self.values[0].id)
            embeds  = build_reglement_embeds()

            for embed in embeds[:-1]:
                await channel.send(embed=embed)
            await channel.send(embed=embeds[-1], view=ReglementView())

            embed = discord.Embed(
                title="◈  RÈGLEMENT ENVOYÉ  ◈",
                description=f"✅ Règlement posté dans {channel.mention}.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsReglementView())
        except Exception as e:
            print(f"❌ ERREUR RÈGLEMENT ENVOI : {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class SettingsReglementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ReglementRoleSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Envoyer le règlement", emoji="📜", style=discord.ButtonStyle.primary)
    async def send_reglement(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  ENVOYER LE RÈGLEMENT  ◈",
            description="Sélectionne le salon où envoyer le règlement.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsReglementChannelView())

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())


class SettingsReglementChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ReglementChannelSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        config  = load_config()
        role_id = config.get("reglement", {}).get("role_id")
        current = f"<@&{role_id}>" if role_id else "*Non configuré*"

        embed = discord.Embed(
            title="◈  SETTINGS — RÈGLEMENT  ◈",
            description=f"**Rôle attribué à l'acceptation :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsReglementView())

# ─────────────────────────────────────────
#  VUE : MENU TICKETS
# ─────────────────────────────────────────

class SettingsTicketsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Envoyer le panel", emoji="📨", style=discord.ButtonStyle.primary)
    async def send_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  ENVOYER LE PANEL  ◈",
            description="Sélectionne le salon où envoyer le panel de tickets.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsPanelChannelView())

    @discord.ui.button(label="Salon de logs", emoji="📋", style=discord.ButtonStyle.primary)
    async def logs_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON DE LOGS  ◈",
            description="Sélectionne le salon où seront envoyés les logs de tickets.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsLogsChannelView())

    @discord.ui.button(label="Gérer les rôles support", emoji="👥", style=discord.ButtonStyle.primary)
    async def manage_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  RÔLES SUPPORT — CATÉGORIE  ◈",
            description="Sélectionne la catégorie de ticket pour gérer ses rôles support.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsRolesCategoryView())

    @discord.ui.button(label="Voir la config", emoji="🔍", style=discord.ButtonStyle.secondary)
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        config         = load_config()
        roles_config   = config["tickets"]["roles"]
        log_channel_id = config["tickets"].get("logs_channel_id")

        embed = discord.Embed(
            title="◈  CONFIG ACTUELLE — TICKETS  ◈",
            color=COLOR_MAIN,
        )
        embed.add_field(
            name="◈ Salon de logs",
            value=f"<#{log_channel_id}>" if log_channel_id else "*Non configuré*",
            inline=False
        )
        for key, label in TICKETS_LABELS.items():
            role_ids = roles_config.get(key, [])
            value    = " ".join([f"<@&{r}>" for r in role_ids]) if role_ids else "*Aucun rôle*"
            embed.add_field(name=label, value=value, inline=False)

        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())

# ─────────────────────────────────────────
#  VUE : SALON PANEL
# ─────────────────────────────────────────

class PanelChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon...",
            channel_types=[discord.ChannelType.text],
            custom_id="panel_channel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            from cogs.tickets import build_panel_embed, TicketSelectView
            channel = interaction.guild.get_channel(self.values[0].id)
            await channel.send(embed=build_panel_embed(), view=TicketSelectView())

            embed = discord.Embed(
                title="◈  PANEL DÉPLOYÉ  ◈",
                description=f"✅ Panel envoyé dans {channel.mention}.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())
        except Exception as e:
            print(f"❌ ERREUR PANEL : {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class SettingsPanelChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(PanelChannelSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SETTINGS — TICKETS  ◈", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())

# ─────────────────────────────────────────
#  VUE : SALON LOGS TICKETS
# ─────────────────────────────────────────

class LogsChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon de logs...",
            channel_types=[discord.ChannelType.text],
            custom_id="logs_channel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            config  = load_config()
            config["tickets"]["logs_channel_id"] = channel.id
            save_config(config)

            embed = discord.Embed(
                title="◈  SALON DE LOGS CONFIGURÉ  ◈",
                description=f"✅ Les logs de tickets seront envoyés dans {channel.mention}.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())
        except Exception as e:
            print(f"❌ ERREUR LOGS : {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class SettingsLogsChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(LogsChannelSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SETTINGS — TICKETS  ◈", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())

# ─────────────────────────────────────────
#  VUE : CATÉGORIE POUR LES RÔLES
# ─────────────────────────────────────────

class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key)
            for key, label in TICKETS_LABELS.items()
        ]
        super().__init__(
            placeholder="Sélectionne une catégorie...",
            options=options,
            custom_id="ticket_category_roles_select"
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        config   = load_config()
        role_ids = config["tickets"]["roles"].get(category, [])
        current  = " ".join([f"<@&{r}>" for r in role_ids]) if role_ids else "*Aucun rôle configuré*"

        embed = discord.Embed(
            title=f"◈  RÔLES — {TICKETS_LABELS[category].upper()}  ◈",
            description=(
                f"**Rôles actuels :** {current}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsRolesEditView(category))


class SettingsRolesCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(TicketCategorySelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SETTINGS — TICKETS  ◈", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsTicketsView())

# ─────────────────────────────────────────
#  VUE : AJOUT / SUPPRESSION RÔLES
# ─────────────────────────────────────────

class AddRoleSelect(discord.ui.RoleSelect):
    def __init__(self, category):
        super().__init__(placeholder="Ajouter un rôle...", custom_id="add_role_select")
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        config   = load_config()
        role_ids = config["tickets"]["roles"].get(self.category, [])
        for role in self.values:
            if role.id not in role_ids:
                role_ids.append(role.id)
        config["tickets"]["roles"][self.category] = role_ids
        save_config(config)

        current = " ".join([f"<@&{r}>" for r in role_ids])
        embed   = discord.Embed(
            title=f"◈  RÔLES — {TICKETS_LABELS[self.category].upper()}  ◈",
            description=f"**Rôles actuels :** {current}\n✅ Rôle ajouté.",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsRolesEditView(self.category))


class RemoveRoleSelect(discord.ui.RoleSelect):
    def __init__(self, category):
        super().__init__(placeholder="Retirer un rôle...", custom_id="remove_role_select")
        self.category = category

    async def callback(self, interaction: discord.Interaction):
        config   = load_config()
        role_ids = config["tickets"]["roles"].get(self.category, [])
        for role in self.values:
            if role.id in role_ids:
                role_ids.remove(role.id)
        config["tickets"]["roles"][self.category] = role_ids
        save_config(config)

        current = " ".join([f"<@&{r}>" for r in role_ids]) if role_ids else "*Aucun rôle*"
        embed   = discord.Embed(
            title=f"◈  RÔLES — {TICKETS_LABELS[self.category].upper()}  ◈",
            description=f"**Rôles actuels :** {current}\n✅ Rôle retiré.",
            color=COLOR_WARN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsRolesEditView(self.category))


class SettingsRolesEditView(discord.ui.View):
    def __init__(self, category):
        super().__init__(timeout=120)
        self.category = category
        self.add_item(AddRoleSelect(category))
        self.add_item(RemoveRoleSelect(category))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  RÔLES SUPPORT — CATÉGORIE  ◈",
            description="Sélectionne la catégorie de ticket pour gérer ses rôles support.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsRolesCategoryView())

# ─────────────────────────────────────────
#  VUE : SONDAGES
# ─────────────────────────────────────────

class SondageLogsSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon de logs sondages...",
            channel_types=[discord.ChannelType.text],
            custom_id="sondage_logs_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            config  = load_config()
            if "sondage" not in config:
                config["sondage"] = {}
            config["sondage"]["logs_channel_id"] = channel.id
            save_config(config)

            embed = discord.Embed(
                title="◈  LOGS SONDAGES CONFIGURÉ  ◈",
                description=f"✅ Les logs des sondages seront envoyés dans {channel.mention}.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsSondageView())
        except Exception as e:
            print(f"❌ ERREUR SONDAGE LOGS : {e}")
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class SettingsSondageView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(SondageLogsSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())

# ─────────────────────────────────────────
#  VUE : MODÉRATION
# ─────────────────────────────────────────

MOD_COMMANDS = {
    "warn":   "⚠️ Warn",
    "kick":   "👢 Kick",
    "ban":    "🔨 Ban",
    "unban":  "✅ Unban",
    "mute":   "🔇 Mute",
    "unmute": "🔊 Unmute",
    "clear":  "🧹 Clear",
}

class ModerationLogsSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon de logs modération...",
            channel_types=[discord.ChannelType.text],
            custom_id="moderation_logs_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            config  = load_config()
            if "moderation" not in config:
                config["moderation"] = {"logs_channel_id": None, "roles": {}}
            config["moderation"]["logs_channel_id"] = channel.id
            save_config(config)

            embed = discord.Embed(
                title="◈  LOGS MODÉRATION CONFIGURÉ  ◈",
                description=f"✅ Les logs de modération seront envoyés dans {channel.mention}.",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsModerationView())
        except Exception as e:
            print(f"❌ ERREUR MOD LOGS : {e}")
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class ModerationCommandSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key)
            for key, label in MOD_COMMANDS.items()
        ]
        super().__init__(
            placeholder="Sélectionne une commande...",
            options=options,
            custom_id="moderation_command_select"
        )

    async def callback(self, interaction: discord.Interaction):
        command  = self.values[0]
        config   = load_config()
        role_ids = config.get("moderation", {}).get("roles", {}).get(command, [])
        current  = " ".join([f"<@&{r}>" for r in role_ids]) if role_ids else "*Aucun rôle configuré*"

        embed = discord.Embed(
            title=f"◈  RÔLES — {MOD_COMMANDS[command].upper()}  ◈",
            description=f"**Rôles autorisés :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationRolesView(command))


class SettingsModerationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ModerationLogsSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Gérer les rôles par commande", emoji="👥", style=discord.ButtonStyle.primary)
    async def manage_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  RÔLES — COMMANDE  ◈",
            description="Sélectionne une commande pour gérer ses rôles autorisés.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationCommandView())

    @discord.ui.button(label="Voir la config", emoji="🔍", style=discord.ButtonStyle.secondary)
    async def view_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config()
        roles  = config.get("moderation", {}).get("roles", {})
        log_id = config.get("moderation", {}).get("logs_channel_id")

        embed = discord.Embed(
            title="◈  CONFIG — MODÉRATION  ◈",
            color=COLOR_MAIN,
        )
        embed.add_field(
            name="◈ Salon de logs",
            value=f"<#{log_id}>" if log_id else "*Non configuré*",
            inline=False
        )
        for key, label in MOD_COMMANDS.items():
            role_ids = roles.get(key, [])
            value    = " ".join([f"<@&{r}>" for r in role_ids]) if role_ids else "*Admins uniquement*"
            embed.add_field(name=label, value=value, inline=False)

        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationView())

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())


class SettingsModerationCommandView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ModerationCommandSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        config     = load_config()
        channel_id = config.get("moderation", {}).get("logs_channel_id")
        current    = f"<#{channel_id}>" if channel_id else "*Non configuré*"
        embed = discord.Embed(
            title="◈  SETTINGS — MODÉRATION  ◈",
            description=f"**Salon de logs actuel :** {current}\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationView())


class AddModRoleSelect(discord.ui.RoleSelect):
    def __init__(self, command):
        super().__init__(placeholder="Ajouter un rôle...", custom_id="add_mod_role_select")
        self.command = command

    async def callback(self, interaction: discord.Interaction):
        config   = load_config()
        if "moderation" not in config:
            config["moderation"] = {"logs_channel_id": None, "roles": {}}
        role_ids = config["moderation"]["roles"].get(self.command, [])
        for role in self.values:
            if role.id not in role_ids:
                role_ids.append(role.id)
        config["moderation"]["roles"][self.command] = role_ids
        save_config(config)

        current = " ".join([f"<@&{r}>" for r in role_ids])
        embed   = discord.Embed(
            title=f"◈  RÔLES — {MOD_COMMANDS[self.command].upper()}  ◈",
            description=f"**Rôles autorisés :** {current}\n✅ Rôle ajouté.",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationRolesView(self.command))


class RemoveModRoleSelect(discord.ui.RoleSelect):
    def __init__(self, command):
        super().__init__(placeholder="Retirer un rôle...", custom_id="remove_mod_role_select")
        self.command = command

    async def callback(self, interaction: discord.Interaction):
        config   = load_config()
        role_ids = config["moderation"]["roles"].get(self.command, [])
        for role in self.values:
            if role.id in role_ids:
                role_ids.remove(role.id)
        config["moderation"]["roles"][self.command] = role_ids
        save_config(config)

        current = " ".join([f"<@&{r}>" for r in role_ids]) if role_ids else "*Aucun rôle*"
        embed   = discord.Embed(
            title=f"◈  RÔLES — {MOD_COMMANDS[self.command].upper()}  ◈",
            description=f"**Rôles autorisés :** {current}\n✅ Rôle retiré.",
            color=COLOR_WARN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationRolesView(self.command))


class SettingsModerationRolesView(discord.ui.View):
    def __init__(self, command):
        super().__init__(timeout=120)
        self.command = command
        self.add_item(AddModRoleSelect(command))
        self.add_item(RemoveModRoleSelect(command))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  RÔLES — COMMANDE  ◈",
            description="Sélectionne une commande pour gérer ses rôles autorisés.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsModerationCommandView())


# ─────────────────────────────────────────
#  VUE : CAPTCHA
# ─────────────────────────────────────────

class CaptchaVerifChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Salon de vérification...",
            channel_types=[discord.ChannelType.text],
            custom_id="captcha_verif_channel"
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        config  = load_config()
        config["captcha"]["verification_channel_id"] = channel.id
        save_config(config)
        embed = discord.Embed(
            title="◈  CAPTCHA — SALON VÉRIFICATION  ◈",
            description=f"✅ Salon de vérification défini : {channel.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())


class CaptchaLogsChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Salon de logs captcha...",
            channel_types=[discord.ChannelType.text],
            custom_id="captcha_logs_channel"
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        config  = load_config()
        config["captcha"]["logs_channel_id"] = channel.id
        save_config(config)
        embed = discord.Embed(
            title="◈  CAPTCHA — SALON LOGS  ◈",
            description=f"✅ Salon de logs défini : {channel.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())


class CaptchaUnverifiedRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Rôle Non vérifié...", custom_id="captcha_unverified_role")

    async def callback(self, interaction: discord.Interaction):
        role   = self.values[0]
        config = load_config()
        config["captcha"]["unverified_role_id"] = role.id
        save_config(config)
        embed = discord.Embed(
            title="◈  CAPTCHA — RÔLE NON VÉRIFIÉ  ◈",
            description=f"✅ Rôle Non vérifié défini : {role.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())


class CaptchaVerifiedRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Rôle Vérifié...", custom_id="captcha_verified_role")

    async def callback(self, interaction: discord.Interaction):
        role   = self.values[0]
        config = load_config()
        config["captcha"]["verified_role_id"] = role.id
        save_config(config)
        embed = discord.Embed(
            title="◈  CAPTCHA — RÔLE VÉRIFIÉ  ◈",
            description=f"✅ Rôle Vérifié défini : {role.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())

class CaptchaVerifChannelChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Créer automatiquement", emoji="🤖", style=discord.ButtonStyle.primary)
    async def create_auto(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Créer le salon avec les bonnes permissions
        config             = load_config()
        unverified_role_id = config.get("captcha", {}).get("unverified_role_id")
        unverified_role    = interaction.guild.get_role(unverified_role_id) if unverified_role_id else None

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True),
        }
        if unverified_role:
            overwrites[unverified_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await interaction.guild.create_text_channel(
            name="✅・vérification",
            overwrites=overwrites,
            topic="Vérification captcha — AERON"
        )

        config["captcha"]["verification_channel_id"] = channel.id
        save_config(config)

        embed = discord.Embed(
            title="◈  SALON CRÉÉ  ◈",
            description=f"✅ Salon de vérification créé : {channel.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())

    @discord.ui.button(label="Choisir un salon existant", emoji="📌", style=discord.ButtonStyle.secondary)
    async def choose_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SALON DE VÉRIFICATION  ◈", description="Sélectionne le salon.", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(CaptchaVerifChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SETTINGS — CAPTCHA  ◈", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())


class CaptchaLogsChannelChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Créer automatiquement", emoji="🤖", style=discord.ButtonStyle.primary)
    async def create_auto(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        channel = await interaction.guild.create_text_channel(
            name="📋・logs-captcha",
            overwrites=overwrites,
            topic="Logs du système de vérification — AERON"
        )

        config = load_config()
        config["captcha"]["logs_channel_id"] = channel.id
        save_config(config)

        embed = discord.Embed(
            title="◈  SALON CRÉÉ  ◈",
            description=f"✅ Salon de logs créé : {channel.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())

    @discord.ui.button(label="Choisir un salon existant", emoji="📌", style=discord.ButtonStyle.secondary)
    async def choose_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SALON DE LOGS  ◈", description="Sélectionne le salon.", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(CaptchaLogsChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SETTINGS — CAPTCHA  ◈", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())


class SettingsCaptchaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Activer / Désactiver", emoji="🔘", style=discord.ButtonStyle.primary)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            config  = load_config()
            if "captcha" not in config:
                config["captcha"] = {"enabled": False}
            current  = config["captcha"].get("enabled", False)
            new_status = not current

            if not current:
                existing = discord.utils.get(interaction.guild.roles, name="Non vérifié")
                if existing:
                    unverified_role = existing
                else:
                    unverified_role = await interaction.guild.create_role(
                        name="Non vérifié",
                        color=discord.Color.from_rgb(150, 150, 150),
                        reason="Système captcha AERON activé"
                    )
                config["captcha"]["unverified_role_id"] = unverified_role.id
                config["captcha"]["enabled"] = True
            else:
                config["captcha"]["enabled"] = False

            save_config(config)

            captcha            = config["captcha"]
            verif_channel_id   = captcha.get("verification_channel_id")
            logs_channel_id    = captcha.get("logs_channel_id")
            verified_role_id   = captcha.get("verified_role_id")
            unverified_role_id = captcha.get("unverified_role_id")

            embed = discord.Embed(
                title="◈  SETTINGS — CAPTCHA  ◈",
                description=(
                    f"**Statut :** {'✅ Activé' if new_status else '❌ Désactivé'}\n"
                    f"**Salon de vérification :** {f'<#{verif_channel_id}>' if verif_channel_id else '*Non configuré*'}\n"
                    f"**Salon de logs :** {f'<#{logs_channel_id}>' if logs_channel_id else '*Non configuré*'}\n"
                    f"**Rôle Non vérifié :** {f'<@&{unverified_role_id}>' if unverified_role_id else '*Non créé*'}\n"
                    f"**Rôle Vérifié :** {f'<@&{verified_role_id}>' if verified_role_id else '*Non configuré*'}\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=COLOR_SUCCESS if new_status else COLOR_DANGER,
            )
            embed.set_thumbnail(url=AERON_LOGO)
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsCaptchaView())

        except Exception as e:
            print(f"❌ ERREUR TOGGLE CAPTCHA : {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)
            except:
                await interaction.followup.send(f"❌ Erreur : `{e}`", ephemeral=True)

    @discord.ui.button(label="Salon vérification", emoji="🔐", style=discord.ButtonStyle.secondary)
    async def verif_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON DE VÉRIFICATION  ◈",
            description=(
                "Comment veux-tu configurer le salon de vérification ?\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 **Créer automatiquement** — Le bot crée le salon\n"
                "📌 **Choisir un salon existant** — Tu sélectionnes ton salon"
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=CaptchaVerifChannelChoiceView())

    @discord.ui.button(label="Salon logs", emoji="📋", style=discord.ButtonStyle.secondary)
    async def logs_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON DE LOGS  ◈",
            description=(
                "Comment veux-tu configurer le salon de logs ?\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 **Créer automatiquement** — Le bot crée le salon\n"
                "📌 **Choisir un salon existant** — Tu sélectionnes ton salon"
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=CaptchaLogsChannelChoiceView())

    @discord.ui.button(label="Rôle Vérifié", emoji="✅", style=discord.ButtonStyle.secondary)
    async def verified_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  RÔLE VÉRIFIÉ  ◈", description="Sélectionne le rôle à donner après vérification.", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(CaptchaVerifiedRoleSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())

# ─────────────────────────────────────────
#  VUE : SALONS VOCAUX
# ─────────────────────────────────────────

class VocalHubChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon \"Créer votre salon\"...",
            channel_types=[discord.ChannelType.voice],
            custom_id="vocal_hub_channel_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(self.values[0].id)
            config  = load_config()
            if "vocal" not in config:
                config["vocal"] = {}
            config["vocal"]["hub_channel_id"] = channel.id
            save_config(config)

            embed = discord.Embed(
                title="◈  SALON VOCAL CONFIGURÉ  ◈",
                description=f"✅ {channel.mention} est maintenant le salon \"Créer votre salon\".",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsVocalView())
        except Exception as e:
            print(f"❌ ERREUR VOCAL HUB : {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class VocalHubChannelChoiceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Créer automatiquement", emoji="🤖", style=discord.ButtonStyle.primary)
    async def create_auto(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            channel = await interaction.guild.create_voice_channel(
                name="➕・Créer votre salon",
                reason="Salon hub de création de vocaux — AERON"
            )

            config = load_config()
            if "vocal" not in config:
                config["vocal"] = {}
            config["vocal"]["hub_channel_id"] = channel.id
            save_config(config)

            embed = discord.Embed(
                title="◈  SALON CRÉÉ  ◈",
                description=f"✅ Salon \"Créer votre salon\" créé : {channel.mention}",
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
            await interaction.response.edit_message(embed=embed, view=SettingsVocalView())
        except Exception as e:
            print(f"❌ ERREUR CRÉATION HUB VOCAL : {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)

    @discord.ui.button(label="Choisir un salon existant", emoji="📌", style=discord.ButtonStyle.secondary)
    async def choose_existing(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON \"CRÉER VOTRE SALON\"  ◈",
            description="Sélectionne le salon vocal existant.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(VocalHubChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="◈  SETTINGS — SALONS VOCAUX  ◈", color=COLOR_MAIN)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsVocalView())


class SettingsVocalView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Salon \"Créer votre salon\"", emoji="🔊", style=discord.ButtonStyle.primary)
    async def hub_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON \"CRÉER VOTRE SALON\"  ◈",
            description=(
                "Comment veux-tu configurer ce salon ?\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🤖 **Créer automatiquement** — Le bot crée le salon\n"
                "📌 **Choisir un salon existant** — Tu sélectionnes ton salon"
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=VocalHubChannelChoiceView())

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings", description="Panneau de configuration AERON")
    async def settings(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Tu n'as pas accès à cette commande.", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=AERON_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, view=SettingsMainView(), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))