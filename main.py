import os
import asyncio
from typing import List, Dict
from typing import Set
from datetime import datetime, timedelta
from discord.ext import tasks
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from discord import ui, app_commands, Interaction
from discord.ui import Button, View, Modal, TextInput
from discord.ext import tasks
import webserver

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree  # VERY IMPORTANT — use existing tree


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")


# הגדר את ה־intents שאתה צריך
intents = discord.Intents.default()
intents.members = True

BOT_TOKEN = 'MTQ0Njg0ODE2MzcyNTE4MDk1OA.Ghvrw0.vmzxD82DVd1Bw8EjPfVCQR9gtAbopDl5K3yO90'

# ==================== Verify Setup ====================#

# הגדרת רולים שמורשים להפעיל את /verify-setup
ALLOWED_ROLE_IDS = [1446863206537494548, 1446863200929710110, 1446862374962462720]  # ← הכנס כאן ID של רולים מורשים

class VerifyButton(discord.ui.View):
    def __init__(self, role: discord.Role):
        super().__init__(timeout=None)
        self.role = role

    @discord.ui.button(label="Verify ✅", style=discord.ButtonStyle.green)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.role in interaction.user.roles:
            return await interaction.response.send_message(
                "כבר יש לך את הרול הזה ✔️", ephemeral=True
            )

        await interaction.user.add_roles(self.role)
        await interaction.response.send_message(
            f"הרול **{self.role.name}** נוסף אליך בהצלחה!", ephemeral=True
        )


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await bot.tree.sync()  # מסנכרן את הסלאש קומנדס


# --- הפקודה /verify-setup ---
@bot.tree.command(name="verify-setup", description="יוצר הודעת אימות עם כפתור ורול נבחר")
@app_commands.describe(
    channel="בחר את החדר שבו תישלח ההודעה",
    role="הרול שיתווסף למשתמש כשלוחצים על הכפתור"
)
async def verify_setup(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    role: discord.Role
):
    # בדיקה אם למבצע הפקודה יש רול מורשה
    if not any(r.id in ALLOWED_ROLE_IDS for r in interaction.user.roles):
        return await interaction.response.send_message(
            "❌ אין לך הרשאה להשתמש בפקודה הזו.",
            ephemeral=True
        )

    embed = discord.Embed(
        title="אימות משתמשים",
        description = (
        "ברוכים הבאים!\n"
        "לפניי שתלחצו על כפתור האימות בבקשה קראו את חוקי השרת. אי ידיעת החוקים אינה פותרת מענישה ❗\n"
        "- יש לדבר בשפה מכובדת מול כל חבריי השרת\n"
        "- אין לשלוח תוכן בין אם זה טקסט, תמונות או גיפים שהם 18+\n"
        "- חובה לפנות לצוות השרת בצורה מכבדת"
        ),
        color=0x2b2d31
    )

    # יצירת כפתור
    view = VerifyButton(role)

    await channel.send(embed=embed, view=view)

    await interaction.response.send_message(
        f"✔️ הודעת אימות נשלחה בהצלחה אל <#{channel.id}>", ephemeral=True
    )

#=================================================#
#==================== Birthday ====================#

BIRTHDAY_ROLE_ID = 1453683957907591332

# user_id: {"day": int, "month": int, "year": Optional[int]}
birthdays = {}

# =========================
# /set-birthday command
# =========================
@bot.tree.command(name="set-birthday", description="הגדרת יום הולדת")
@app_commands.describe(
    day="יום בחודש",
    month="חודש",
    year="שנת לידה (לא חובה)"
)
async def set_birthday(
    interaction: discord.Interaction,
    day: int,
    month: int,
    year: int | None = None
):
    if interaction.channel_id != BIRTHDAY_CHANNEL_ID:
        return await interaction.response.send_message(
            "❌ ניתן להשתמש בפקודה רק בחדר הייעודי.", ephemeral=True
        )

    if not (1 <= day <= 31 and 1 <= month <= 12):
        return await interaction.response.send_message(
            "❌ תאריך לא חוקי.", ephemeral=True
        )

    birthdays[interaction.user.id] = {
        "day": day,
        "month": month,
        "year": year
    }

    await interaction.response.send_message(
        "🎂 יום ההולדת שלך נשמר בהצלחה!", ephemeral=True
    )

# =========================
# Birthday checker (daily)
# =========================
@tasks.loop(minutes=60)
async def birthday_check():
    now = datetime.now()
    guilds = bot.guilds

    for guild in guilds:
        role = guild.get_role(BIRTHDAY_ROLE_ID)
        channel = guild.get_channel(BIRTHDAY_CHANNEL_ID)

        if not role or not channel:
            continue

        for user_id, data in birthdays.items():
            if data["day"] == now.day and data["month"] == now.month:
                member = guild.get_member(user_id)
                if not member or role in member.roles:
                    continue

                # Add role
                await member.add_roles(role)

                # Build message
                if data.get("year"):
                    age = now.year - data["year"]
                    msg = f"🎉 מזל טוב ל־{member.mention} שחוגג היום {age}! 🎂"
                else:
                    msg = f"🎉 מזל טוב ל־{member.mention}! 🎂 מאחלים לך יום מלא שמחה והצלחה!"

                await channel.send(msg)

                # Remove role after 24h
                async def remove_role_later(m=member):
                    await asyncio.sleep(86400)
                    await m.remove_roles(role)

                bot.loop.create_task(remove_role_later())

# =========================
# Cleanup messages in channel
# =========================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.channel.id == BIRTHDAY_CHANNEL_ID:
        if not message.content.startswith("/set-birthday"):
            await message.delete()
            return

    await bot.process_commands(message)

# =========================
# Instruction Embed (on ready)
# =========================
BIRTHDAY_CHANNEL_ID = 1453683149941899508

@bot.tree.command(name="birthday-help", description="שליחת הסבר על פקודת יום הולדת")
async def birthday_help(interaction: discord.Interaction):

    if interaction.channel_id != BIRTHDAY_CHANNEL_ID:
        return await interaction.response.send_message(
            "❌ ניתן להשתמש בפקודה זו רק בחדר הייעודי.", ephemeral=True
        )

    embed = discord.Embed(
        title="🎂 הגדרת יום הולדת",
        description=(
            "כדי להגדיר את יום ההולדת שלך השתמש בפקודה:\n\n"
            "**/set-birthday יום חודש [שנה]**\n\n"
            "**דוגמאות:**\n"
            "`/set-birthday 14 6`\n"
            "`/set-birthday 14 6 2008`\n\n"
            "📌 השנה *לא חובה*\n"
            "🎁 ביום ההולדת תקבל רול מיוחד וברכה 🎉"
        ),
        color=0x5865F2
    )

    await interaction.response.send_message(embed=embed)

#=================================================#
#==================== Welcome ====================#
WELCOME_CHANNEL_ID = 1446864711684591761

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        return  # אם הערוץ לא נמצא

    member_count = member.guild.member_count

    embed = discord.Embed(
        description=f"{member.mention}\n"
                    f"**אתה החבר ה-{member_count} בשרת!**",
        color=0x00ff00
    )
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"User ID: {member.id}")

    await channel.send(embed=embed)
#=================================================#
#==================== Costum Voices ====================#
import discord
from discord import ui, app_commands, Interaction
from discord.ui import Button, View, Modal, TextInput
import asyncio

# מילון לעקוב אחרי חדרי קול מותאמים של משתמשים (זמני - לא שורד restart)
user_channels = {}  # user_id: channel_id

ALLOWED_ROLES = [1446862374962462720, 1446863206537494548]

# ID של הקטגוריה שבה ייווצרו כל חדרי ה-Costume Voice
COSTUME_CATEGORY_ID = 1453689472100073482

# פונקציית מחיקה אוטומטית של חדר ריק אחרי 5 דקות
async def auto_delete_empty_channel(channel_id: int, owner_id: int):
    await asyncio.sleep(300)  # 5 דקות

    channel = bot.get_channel(channel_id)
    if channel is None:
        if owner_id in user_channels:
            del user_channels[owner_id]
        return

    # בודק אם יש מישהו בחדר (מתעלם מבוטים)
    if len([m for m in channel.members if not m.bot]) > 0:
        return

    # החדר ריק - מוחקים אותו
    await channel.delete()
    if owner_id in user_channels:
        del user_channels[owner_id]

class BlockModal(Modal, title="חסימת משתמש"):
    user_id_input = TextInput(label="Discord User ID", style=discord.TextStyle.short, placeholder="הזן את ה-ID של המשתמש")

    async def on_submit(self, interaction: Interaction):
        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)
            return

        if interaction.user.id not in user_channels:
            await interaction.response.send_message("אין לך חדר קולי פעיל.", ephemeral=True)
            return

        try:
            target_id = int(self.user_id_input.value.strip())
            target_member = await interaction.guild.fetch_member(target_id)
        except ValueError:
            await interaction.response.send_message("ה-ID שהזנת אינו תקין.", ephemeral=True)
            return
        except discord.NotFound:
            await interaction.response.send_message("משתמש עם ID זה לא נמצא בשרת.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(user_channels[interaction.user.id])
        if channel is None:
            del user_channels[interaction.user.id]
            await interaction.response.send_message("החדר שלך נמחק או לא נמצא.", ephemeral=True)
            return

        await channel.set_permissions(target_member, connect=False)
        await interaction.response.send_message(f"חסמת את {target_member.mention} מהחדר שלך.", ephemeral=True)

class UnblockModal(Modal, title="ביטול חסימה"):
    user_id_input = TextInput(label="Discord User ID", style=discord.TextStyle.short, placeholder="הזן את ה-ID של המשתמש")

    async def on_submit(self, interaction: Interaction):
        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)
            return

        if interaction.user.id not in user_channels:
            await interaction.response.send_message("אין לך חדר קולי פעיל.", ephemeral=True)
            return

        try:
            target_id = int(self.user_id_input.value.strip())
            target_member = await interaction.guild.fetch_member(target_id)
        except ValueError:
            await interaction.response.send_message("ה-ID שהזנת אינו תקין.", ephemeral=True)
            return
        except discord.NotFound:
            await interaction.response.send_message("משתמש עם ID זה לא נמצא בשרת.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(user_channels[interaction.user.id])
        if channel is None:
            del user_channels[interaction.user.id]
            await interaction.response.send_message("החדר שלך נמחק או לא נמצא.", ephemeral=True)
            return

        await channel.set_permissions(target_member, connect=None)  # מחזיר לברירת מחדל
        await interaction.response.send_message(f"ביטלת חסימה ל-{target_member.mention}.", ephemeral=True)

class CostumeVoiceView(View):
    def __init__(self):
        super().__init__(timeout=None)  # persistent view

    @ui.button(label="Create Channel", style=discord.ButtonStyle.primary)
    async def create_channel(self, interaction: Interaction, button: Button):
        if not any(role.id in ALLOWED_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("אין לך הרשאה להשתמש בפקודה זו.", ephemeral=True)
            return

        if interaction.user.id in user_channels:
            channel = interaction.guild.get_channel(user_channels[interaction.user.id])
            if channel:
                await interaction.response.send_message(f"כבר יש לך חדר קולי פעיל: {channel.mention}", ephemeral=True)
            else:
                del user_channels[interaction.user.id]
            return

        # מציאת הקטגוריה
        category = interaction.guild.get_channel(COSTUME_CATEGORY_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("קטגוריית ה-Costume Voice לא נמצאה או אינה תקינה.", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            interaction.user: discord.PermissionOverwrite(
                manage_channels=True,
                mute_members=True,
                deafen_members=True,
                move_members=True,
                connect=True,
                view_channel=True
            )
        }

        channel = await interaction.guild.create_voice_channel(
            name=f"{interaction.user.name}'s voice",
            category=category,          # <--- כאן נוצר החדר בתוך הקטגוריה הנכונה
            overwrites=overwrites,
            reason=f"Costume Voice שנוצר על ידי {interaction.user}"
        )

        user_channels[interaction.user.id] = channel.id

        # הפעלת מחיקה אוטומטית אם ריק 5 דקות
        bot.loop.create_task(auto_delete_empty_channel(channel.id, interaction.user.id))

        await interaction.response.send_message(
            f"נוצר חדר קולי בהצלחה: {channel.mention}\n"
            "החדר יימחק אוטומטית אם יהיה ריק למשך 5 דקות.",
            ephemeral=True
        )

    @ui.button(label="Lock Channel", style=discord.ButtonStyle.secondary)
    async def lock_channel(self, interaction: Interaction, button: Button):
        if interaction.user.id not in user_channels:
            await interaction.response.send_message("אין לך חדר קולי פעיל.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(user_channels[interaction.user.id])
        if channel is None:
            del user_channels[interaction.user.id]
            await interaction.response.send_message("החדר שלך נמחק.", ephemeral=True)
            return

        await channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("החדר ננעל - רק אתה יכול להיכנס.", ephemeral=True)

    @ui.button(label="Unlock Channel", style=discord.ButtonStyle.secondary)
    async def unlock_channel(self, interaction: Interaction, button: Button):
        if interaction.user.id not in user_channels:
            await interaction.response.send_message("אין לך חדר קולי פעיל.", ephemeral=True)
            return

        channel = interaction.guild.get_channel(user_channels[interaction.user.id])
        if channel is None:
            del user_channels[interaction.user.id]
            await interaction.response.send_message("החדר שלך נמחק.", ephemeral=True)
            return

        await channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("החדר נפתח - כולם יכולים להיכנס.", ephemeral=True)

    @ui.button(label="Block Member", style=discord.ButtonStyle.danger)
    async def block_member(self, interaction: Interaction, button: Button):
        if interaction.user.id not in user_channels:
            await interaction.response.send_message("אין לך חדר קולי פעיל.", ephemeral=True)
            return
        await interaction.response.send_modal(BlockModal())

    @ui.button(label="Unblock Member", style=discord.ButtonStyle.success)
    async def unblock_member(self, interaction: Interaction, button: Button):
        if interaction.user.id not in user_channels:
            await interaction.response.send_message("אין לך חדר קולי פעיל.", ephemeral=True)
            return
        await interaction.response.send_modal(UnblockModal())

# הפקודה /costume-voice
@bot.tree.command(name="costume-voice", description="הפעלת מערכת חדרי קול מותאמים אישית")
@app_commands.checks.has_any_role(*ALLOWED_ROLES)
async def costume_voice(interaction: Interaction):
    channel = bot.get_channel(1453689714925371455)
    if channel is None:
        await interaction.response.send_message("ערוץ ההסבר לא נמצא (ID שגוי?).", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎙️ מערכת Costume Voice",
        description="ניהול חדר קול פרטי ומתקדם!\n\n"
                    "• **Create Channel** – יוצר חדר קולי אישי בשם `<שמך>'s voice`\n"
                    "• מותר **חדר אחד בלבד** לכל משתמש\n"
                    "• רק לך יש הרשאות: שינוי שם, Server Mute, Server Deafen, Disconnect\n"
                    "• **Lock Channel** – נועל את החדר (רק אתה יכול להיכנס, כולם רואים)\n"
                    "• **Unlock Channel** – פותח לכולם\n"
                    "• **Block/Unblock Member** – חסימה או ביטול חסימה של משתמש ספציפי\n"
                    "• החדר נמחק אוטומטית אם ריק למשך **5 דקות**\n"
                    "• כל החדרים נוצרים בתוך הקטגוריה הייעודית",
        color=0x00ff00
    )
    embed.set_footer(text="רק בעלי תפקידים מורשים יכולים להשתמש")

    view = CostumeVoiceView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message("ההודעה עם הכפתורים נשלחה לערוץ ההסבר!", ephemeral=True)
#=================================================#
#==================== Staff List ====================#
STAFF_LIST_CHANNEL_ID = 1448611972664000522

ALLOWED_PANEL_ROLES = {
    1446862374962462720,
    1446863206537494548,
    1446862377009021064
}

STAFF_ROLES_MAP = {
    "Support Team《🦺》": 1446851246261534933,
    "Admin《👔》": 1446851395235090623,
    "Head Admin《🖇️》": 1446860353211207700,
    "Staff Manager《🪪》": 1446859437334728847,
    "Management《⚖️》": 1446863163734884494,
}

staff_list_message_id = None


def has_any_role(member: discord.Member, roles: set[int]) -> bool:
    return any(role.id in roles for role in member.roles)


def build_staff_list_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(title="__Staff List__", color=0x2b2d31)

    for title, role_id in STAFF_ROLES_MAP.items():
        role = guild.get_role(role_id)
        members = [m.mention for m in role.members] if role else []
        value = "\n".join(members) if members else "—"

        embed.add_field(name=f"**{title}**", value=value, inline=False)

    return embed


@bot.tree.command(name="staff-list")
async def staff_list(interaction: discord.Interaction):
    global staff_list_message_id

    if not has_any_role(interaction.user, ALLOWED_PANEL_ROLES):
        return await interaction.response.send_message("❌ אין לך הרשאה.", ephemeral=True)

    channel = interaction.guild.get_channel(STAFF_LIST_CHANNEL_ID)
    embed = build_staff_list_embed(interaction.guild)

    msg = await channel.send(embed=embed)
    staff_list_message_id = msg.id

    await interaction.response.send_message("✅ Staff List נשלח.", ephemeral=True)


@tasks.loop(minutes=10)
async def update_staff_list():
    if not staff_list_message_id:
        return

    for guild in bot.guilds:
        channel = guild.get_channel(STAFF_LIST_CHANNEL_ID)
        try:
            msg = await channel.fetch_message(staff_list_message_id)
            await msg.edit(embed=build_staff_list_embed(guild))
        except:
            pass


@bot.event
async def on_ready():
    update_staff_list.start()
#=================================================#
#==================== Staff Warning ====================#
STAFF_WARNING_CHANNEL_ID = 1448612048840818690

ALLOWED_PANEL_ROLES = {
    1446862374962462720,
    1446863206537494548,
    1446862377009021064
}

WARNING_COMMAND_ROLES = {
    1446859176432111749,
    1446862377009021064,
    1446862374962462720,
    1446863206537494548
}

STAFF_ROLES_MAP = {
    "Support Team《🦺》": 1446851246261534933,
    "Admin《👔》": 1446851395235090623,
    "Head Admin《🖇️》": 1446860353211207700,
    "Staff Manager《🪪》": 1446859437334728847,
    "Management《⚖️》": 1446863163734884494,
}

warnings = {}  # user_id -> count
staff_warning_message_id = None


def has_any_role(member: discord.Member, roles: set[int]) -> bool:
    return any(role.id in roles for role in member.roles)


def build_warning_embed(guild: discord.Guild) -> discord.Embed:
    embed = discord.Embed(title="__Staff List__", color=0x2b2d31)

    for title, role_id in STAFF_ROLES_MAP.items():
        role = guild.get_role(role_id)
        if not role or not role.members:
            value = "—"
        else:
            lines = []
            for m in role.members:
                count = warnings.get(m.id, 0)
                lines.append(f"{m.mention} - {count} warning{'s' if count != 1 else ''}")
            value = "\n".join(lines)

        embed.add_field(name=f"**{title}**", value=value, inline=False)

    return embed


@bot.tree.command(name="staff_warning_panel")
async def staff_warning_panel(interaction: discord.Interaction):
    global staff_warning_message_id

    if not has_any_role(interaction.user, ALLOWED_PANEL_ROLES):
        return await interaction.response.send_message("❌ אין לך הרשאה.", ephemeral=True)

    channel = interaction.guild.get_channel(STAFF_WARNING_CHANNEL_ID)
    embed = build_warning_embed(interaction.guild)

    msg = await channel.send(embed=embed)
    staff_warning_message_id = msg.id

    await interaction.response.send_message("✅ Staff Warning Panel נשלח.", ephemeral=True)


@bot.tree.command(name="add_warning")
async def add_warning(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not has_any_role(interaction.user, WARNING_COMMAND_ROLES):
        return await interaction.response.send_message("❌ אין לך הרשאה.", ephemeral=True)

    warnings[member.id] = warnings.get(member.id, 0) + amount
    await interaction.response.send_message("✅ Warning נוסף.", ephemeral=True)
    await refresh_warning_panel(interaction.guild)


@bot.tree.command(name="remove_warning")
async def remove_warning(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not has_any_role(interaction.user, WARNING_COMMAND_ROLES):
        return await interaction.response.send_message("❌ אין לך הרשאה.", ephemeral=True)

    warnings[member.id] = max(0, warnings.get(member.id, 0) - amount)
    await interaction.response.send_message("✅ Warning הוסר.", ephemeral=True)
    await refresh_warning_panel(interaction.guild)


async def refresh_warning_panel(guild: discord.Guild):
    if not staff_warning_message_id:
        return

    channel = guild.get_channel(STAFF_WARNING_CHANNEL_ID)
    try:
        msg = await channel.fetch_message(staff_warning_message_id)
        await msg.edit(embed=build_warning_embed(guild))
    except:
        pass


@tasks.loop(minutes=10)
async def auto_update_warning_panel():
    for guild in bot.guilds:
        await refresh_warning_panel(guild)


@bot.event
async def on_ready():
    auto_update_warning_panel.start()
#=================================================#
#==================== Tickets ====================#
# -----------------------
# הגדרות בסיסיות
# -----------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = False


# STAFF ROLES קבועים כפי שביקשת
STAFF_ROLES = [
    1446851193732337827,
    1446859176432111749,
    1446862330376749087,
    1446862377009021064,
    1446863200929710110,
    1446863206537494548,
    1446862374962462720
]

# רול לתג בברוך הבא בתוך הטיקט
WELCOME_ROLE_ID = 1446851193732337827

# קטגוריות פתיחה (רק אליהם ניתן לפתוח טיקט)
CATEGORY_MAP = {
    "question": 1447221860675616829,
    "purchase": 1447222078016065536,
    "complaint": 1447222150686572574,
}

# קטגוריות זמינות לשינוי (כולל High Staff ו-Other)
CHANGE_CATEGORY_MAP = {
    "question": 1447221860675616829,
    "purchase": 1447222078016065536,
    "complaint": 1447222150686572574,
    "highstaff": 1447222276675338291,
    "other": 1447222214578667672,
}

# קטגוריות שמאפשרות שימוש ב-/high /freeze /unfreeze (החמישה)
ALLOWED_TICKET_CATEGORIES = set(CHANGE_CATEGORY_MAP.values())

# לוג HTML קובץ destination
TICKET_LOG_CHANNEL_ID = 1447225499305771090

# הגבלה של עד 2 טיקטים פתוחים למשתמש
MAX_OPEN_TICKETS_PER_USER = 2

# מבני נתונים בזיכרון
# ticket_data[channel_id] = { "opener": user_id, "type": "question"/..., "category_id": id }
ticket_data: Dict[int, Dict] = {}
open_tickets_by_user: Dict[int, Set[int]] = {}

# רשימות רולים ל-high/freeze
HIGH_ALLOWED_ROLES = [1446859176432111749, 1446862330376749087, 1446862377009021064, 1446862374962462720]
FREEZE_WRITE_ROLES = [1446859176432111749, 1446862330376749087, 1446862377009021064, 1446862374962462720]

# -----------------------
# Utilities
# -----------------------
def is_staff_member(member: discord.Member) -> bool:
    return any(role.id in STAFF_ROLES for role in member.roles)

def channel_is_allowed_ticket_category(channel: discord.TextChannel) -> bool:
    if not isinstance(channel, discord.abc.GuildChannel):
        return False
    return (channel.category_id is not None) and (channel.category_id in ALLOWED_TICKET_CATEGORIES)

async def create_ticket_channel(guild: discord.Guild, opener: discord.Member, ticket_type: str, category_id: int):
    # שם שימושי: username's <type>
    name_user = opener.name
    ticket_name = f"{name_user}'s {ticket_type}"

    category = guild.get_channel(category_id)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        opener: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    # הרשאות לצוות
    for r_id in STAFF_ROLES:
        role = guild.get_role(r_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    channel = await guild.create_text_channel(name=ticket_name, category=category, overwrites=overwrites)
    return channel

# -----------------------
# Modals
# -----------------------
class DeleteModal(discord.ui.Modal, title="Close Ticket - Reason"):
    reason = discord.ui.TextInput(label="סיבת סגירת הטיקט", style=discord.TextStyle.long, required=True, max_length=500)

    def __init__(self, channel_id: int, closer: discord.Member):
        super().__init__()
        self.channel_id = channel_id
        self.closer = closer

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("ערוץ לא נמצא.", ephemeral=True)

        data = ticket_data.get(channel.id)
        if not data:
            return await interaction.response.send_message("הטיקט לא נמצא במערכת.", ephemeral=True)

        opener_id = data.get("opener")
        opener = guild.get_member(opener_id)
        reason_text = self.reason.value

        await channel.send(f"**הטיקט ייסגר בעוד כ-5 שניות.** סיבת סגירה: {reason_text}")
        await asyncio.sleep(5)

        # שלח DM למי שפתח
        if opener:
            try:
                await opener.send(f"הטיקט שלך `{channel.name}` נסגר על ידי {self.closer.mention}. סיבה: {reason_text}")
            except Exception:
                pass

        # נקה זיכרון
        ticket_data.pop(channel.id, None)
        if opener_id in open_tickets_by_user:
            open_tickets_by_user[opener_id].discard(channel.id)

        # מחק ערוץ
        try:
            await channel.delete(reason=f"Closed by {self.closer}")
        except Exception:
            pass

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message("שגיאה בסגירת הטיקט.", ephemeral=True)

class RenameModal(discord.ui.Modal, title="Rename Ticket"):
    new_name = discord.ui.TextInput(label="שם חדש לטיקט (עד 20 תווים)", required=True, max_length=20)

    def __init__(self, channel_id: int, changer: discord.Member):
        super().__init__()
        self.channel_id = channel_id
        self.changer = changer

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("ערוץ לא נמצא.", ephemeral=True)
        data = ticket_data.get(channel.id)
        if not data:
            return await interaction.response.send_message("הטיקט לא נתמך.", ephemeral=True)
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)

        old = channel.name
        new = self.new_name.value
        try:
            await channel.edit(name=new[:20])
            await channel.send(f"{interaction.user.mention} שינה את שם הטיקט מ־`{old}` ל־`{new}`")
        except Exception as e:
            await interaction.response.send_message(f"שגיאה בשינוי שם: {e}", ephemeral=True)

class AddMemberModal(discord.ui.Modal, title="Add Member to Ticket"):
    member_id = discord.ui.TextInput(label="Discord ID של המשתמש להוספה", required=True, max_length=30)

    def __init__(self, channel_id: int, adder: discord.Member):
        super().__init__()
        self.channel_id = channel_id
        self.adder = adder

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        data = ticket_data.get(channel.id) if channel else None
        if not channel or not data:
            return await interaction.response.send_message("הטיקט לא נמצא.", ephemeral=True)
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)

        try:
            target_id = int(self.member_id.value.strip())
            member = guild.get_member(target_id)
            if not member:
                return await interaction.response.send_message("האיידי לא נמצא בשרת.", ephemeral=True)
            await channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
            await channel.send(f"{interaction.user.mention} הוסיף את {member.mention} לטיקט.")
        except ValueError:
            await interaction.response.send_message("האיידי לא חוקי.", ephemeral=True)

class RemoveMemberModal(discord.ui.Modal, title="Remove Member from Ticket"):
    member_id = discord.ui.TextInput(label="Discord ID של המשתמש להסרה", required=True, max_length=30)

    def __init__(self, channel_id: int, remover: discord.Member):
        super().__init__()
        self.channel_id = channel_id
        self.remover = remover

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        channel = guild.get_channel(self.channel_id)
        data = ticket_data.get(channel.id) if channel else None
        if not channel or not data:
            return await interaction.response.send_message("הטיקט לא נמצא.", ephemeral=True)
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)

        try:
            target_id = int(self.member_id.value.strip())
            member = guild.get_member(target_id)
            if not member:
                return await interaction.response.send_message("האיידי לא נמצא בשרת.", ephemeral=True)
            await channel.set_permissions(member, overwrite=None)
            await channel.send(f"{interaction.user.mention} הסיר את {member.mention} מהטיקט.")
        except ValueError:
            await interaction.response.send_message("האיידי לא חוקי.", ephemeral=True)

# -----------------------
# Buttons / Views
# -----------------------
class TicketClaimButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Staff Claim", style=discord.ButtonStyle.secondary, custom_id="ticket_claim_btn")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not channel:
            return await interaction.response.send_message("שגיאה.", ephemeral=True)
        data = ticket_data.get(channel.id)
        if not data:
            return await interaction.response.send_message("זה לא טיקט נתמך.", ephemeral=True)
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה לבצע Claim.", ephemeral=True)

        # השבת הכפתור ושנה טקסט
        self.disabled = True
        self.label = f"{interaction.user.display_name}'s claim"
        try:
            await interaction.response.edit_message(view=self.view)
        except Exception:
            await interaction.response.send_message("Claim בוצע.", ephemeral=True)

        await channel.send(f"{interaction.user.mention} has claimed this ticket.")

class StaffMenuButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Staff Menu", style=discord.ButtonStyle.primary, custom_id="staff_menu_btn")

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        data = ticket_data.get(channel.id)
        if not data:
            return await interaction.response.send_message("זה לא טיקט נתמך.", ephemeral=True)
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה לפתוח תפריט צוות.", ephemeral=True)

        view = discord.ui.View(timeout=None)
        view.add_item(DeleteTicketButton(channel.id, interaction.user))
        view.add_item(RenameTicketButton(channel.id))
        view.add_item(ChangeCategoryButton(channel.id))
        view.add_item(AddMemberButton(channel.id))
        view.add_item(RemoveMemberButton(channel.id))

        embed = discord.Embed(title="Staff Menu", description="ברוך הבא לתפריט הצוות! בחר את האופציות אשר בהם תרצה להשתמש.", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class DeleteTicketButton(discord.ui.Button):
    def __init__(self, channel_id: int, actor: discord.Member):
        super().__init__(label="Delete", style=discord.ButtonStyle.danger, custom_id=f"delete_btn_{channel_id}")
        self.channel_id = channel_id
        self.actor = actor

    async def callback(self, interaction: discord.Interaction):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)
        modal = DeleteModal(self.channel_id, interaction.user)
        await interaction.response.send_modal(modal)

class RenameTicketButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="Rename", style=discord.ButtonStyle.secondary, custom_id=f"rename_btn_{channel_id}")
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)
        modal = RenameModal(self.channel_id, interaction.user)
        await interaction.response.send_modal(modal)

class ChangeCategoryButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="Change Category", style=discord.ButtonStyle.success, custom_id=f"change_cat_btn_{channel_id}")
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)

        view = discord.ui.View(timeout=60)
        # כפתורים לכל קטגוריה (כחולי)
        for name, cid in CHANGE_CATEGORY_MAP.items():
            async def make_cb(inter, target_cid=cid, cat_name=name):
                channel = inter.guild.get_channel(self.channel_id)
                try:
                    await channel.edit(category=inter.guild.get_channel(target_cid))
                    ticket_data[channel.id]["category_id"] = target_cid
                    await inter.response.send_message(f"{inter.user.mention} העביר את הטיקט לקטגוריה: {cat_name}", ephemeral=False)
                except Exception as e:
                    await inter.response.send_message(f"שגיאה: {e}", ephemeral=True)

            btn = discord.ui.Button(label=name.capitalize(), style=discord.ButtonStyle.secondary)
            btn.callback = make_cb
            view.add_item(btn)

        await interaction.response.send_message("בחר קטגוריה להעברה:", view=view, ephemeral=True)

class AddMemberButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="Add Member", style=discord.ButtonStyle.secondary, custom_id=f"add_member_btn_{channel_id}")
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)
        modal = AddMemberModal(self.channel_id, interaction.user)
        await interaction.response.send_modal(modal)

class RemoveMemberButton(discord.ui.Button):
    def __init__(self, channel_id: int):
        super().__init__(label="Remove Member", style=discord.ButtonStyle.secondary, custom_id=f"remove_member_btn_{channel_id}")
        self.channel_id = channel_id

    async def callback(self, interaction: discord.Interaction):
        if not is_staff_member(interaction.user):
            return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)
        modal = RemoveMemberModal(self.channel_id, interaction.user)
        await interaction.response.send_modal(modal)

# -----------------------
# Ticket Panel (Select menu)
# -----------------------
class TicketPanelSelect(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(label="Question", value="question", description="שאלות כלליות"),
            discord.SelectOption(label="Purchase", value="purchase", description="בעיות רכישה"),
            discord.SelectOption(label="Complaint", value="complaint", description="תלונות")
        ]
        select = discord.ui.Select(placeholder="בחר קטגוריה לפתיחת טיקט...", min_values=1, max_values=1, options=options, custom_id="ticket_panel_select")
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        choice = interaction.data["values"][0]
        guild = interaction.guild
        user = interaction.user

        # בדוק כמות טיקטים פתוחים
        user_open = open_tickets_by_user.get(user.id, set())
        if len(user_open) >= MAX_OPEN_TICKETS_PER_USER:
            return await interaction.response.send_message(f"יש לך כבר {len(user_open)} טיקט/ים פתוחים. ניתן לפתוח עד {MAX_OPEN_TICKETS_PER_USER}.", ephemeral=True)

        category_id = CATEGORY_MAP.get(choice)
        if not category_id:
            return await interaction.response.send_message("קטגוריה זו לא מוגדרת לפתיחה.", ephemeral=True)

        # צור חדר
        try:
            channel = await create_ticket_channel(guild, user, choice, category_id)
        except Exception as e:
            return await interaction.response.send_message(f"שגיאה ביצירת טיקט: {e}", ephemeral=True)

        # עדכן זיכרון
        ticket_data[channel.id] = {"opener": user.id, "type": choice, "category_id": category_id}
        open_tickets_by_user.setdefault(user.id, set()).add(channel.id)

        # שלח embed עם תיוג רול לפני ה-embed
        welcome_role = guild.get_role(WELCOME_ROLE_ID)
        mention_text = welcome_role.mention if welcome_role else f"<@{WELCOME_ROLE_ID}>"
        embed = discord.Embed(title="ברוך הבא לטיקט שלך!", description="בבקשה תמתין למענה מאחד מחבריי הצוות שלנו אשר יפנו אלייך בהקדם האפשרי.", color=0x2b2d31)
        await channel.send(content=mention_text, embed=embed)

        # שלח כפתורי Staff: Claim + Staff Menu (שימוש ברולים קבועים)
        view = discord.ui.View(timeout=None)
        view.add_item(TicketClaimButton())
        view.add_item(StaffMenuButton())
        await channel.send("פעולות צוות:", view=view)

        await interaction.response.send_message(f"✅ הטיקט נפתח: {channel.mention}", ephemeral=True)

# -----------------------
# Slash command: ticket-setup
# -----------------------
@bot.tree.command(name="ticket-setup", description="יוצר פאנל פתיחת טיקטים (Question/Purchase/Complaint)")
@app_commands.describe(channel="בחר את החדר שבו יישלח הפאנל")
async def ticket_setup(interaction: discord.Interaction, channel: discord.TextChannel):
    # בדיקה: הרשאת הפעלת הפקודה (מנהל שרת או סטאף)
    if not (interaction.user.guild_permissions.manage_guild or is_staff_member(interaction.user)):
        return await interaction.response.send_message("אין לך הרשאה להשתמש בפקודה זו.", ephemeral=True)

    embed = discord.Embed(title="Ticket Panel", description=(
        "עבור פתיחת טיקט וקבלת תמיכה מהצוות שלנו, בחרו קטגוריה מבין האפשרויות למטה והמתינו למענה מאחד מחברי הצוות."
        "\n\nהמשך יום נפלא."
    ), color=0x2b2d31)
    view = TicketPanelSelect()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(f"פאנל נשלח אל {channel.mention}", ephemeral=True)

# -----------------------
# /high /freeze /unfreeze
# -----------------------
from discord import app_commands


@bot.tree.command(name="high", description="Lock the ticket but allow the ticket owner + staff.")
async def high(interaction: discord.Interaction):

    staff_role_id = 1446859176432111749
    staff_role = interaction.guild.get_role(staff_role_id)

    if staff_role not in interaction.user.roles:
        return await interaction.response.send_message(
            "❌ אין לך הרשאה להשתמש בפקודה זו.", ephemeral=True
        )

    channel = interaction.channel

    # ----- מוצא את המשתמש מהשם של החדר -----
    # למשל:   tomcupcake's question
    try:
        ticket_owner_name = channel.name.split("'s")[0]
        ticket_owner = discord.utils.get(interaction.guild.members, name=ticket_owner_name)
    except:
        ticket_owner = None

    overwrite = discord.PermissionOverwrite(
        send_messages=False,
        add_reactions=False
    )

    # חוסם את כולם מלבד הצוות + פותח הטיקט
    for member in interaction.guild.members:
        if staff_role not in member.roles and member != ticket_owner:
            try:
                await channel.set_permissions(member, overwrite=overwrite)
            except:
                pass

    # נוודא שפותח הטיקט מקבל הרשאה לכתוב
    if ticket_owner:
        await channel.set_permissions(ticket_owner, send_messages=True, view_channel=True)

    await interaction.response.send_message("⏫ הטיקט קיבל מצב HIGH — רק צוות ופותח הטיקט יכולים לכתוב.", ephemeral=True)


@bot.tree.command(name="freeze", description="Lock the ticket so only staff can talk.")
async def freeze(interaction: discord.Interaction):

    staff_role_id = 1446859176432111749
    staff_role = interaction.guild.get_role(staff_role_id)

    if staff_role not in interaction.user.roles:
        return await interaction.response.send_message(
            "❌ אין לך הרשאה להשתמש בפקודה זו.", ephemeral=True
        )

    channel = interaction.channel

    overwrite = discord.PermissionOverwrite(
        send_messages=False,
        add_reactions=False
    )

    for member in interaction.guild.members:
        if staff_role not in member.roles:
            try:
                await channel.set_permissions(member, overwrite=overwrite)
            except:
                pass

    await interaction.response.send_message("🔒 הטיקט הוקפא — רק צוות גבוהה יכול לכתוב.", ephemeral=True)


@bot.tree.command(name="unfreeze", description="מחזיר את ההרשאה לכולם לכתוב בטיקט")
async def cmd_unfreeze(interaction: discord.Interaction):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("לא בתוך צ'אנל טקסט תקין.", ephemeral=True)
    if not channel_is_allowed_ticket_category(channel):
        return await interaction.response.send_message("לא אפשרי להשתמש בפקודה זו בחדר זה.", ephemeral=True)
    data = ticket_data.get(channel.id)
    if not data:
        return await interaction.response.send_message("זה לא טיקט נתמך.", ephemeral=True)
    if not is_staff_member(interaction.user):
        return await interaction.response.send_message("אין לך הרשאה.", ephemeral=True)

    guild = interaction.guild
    await channel.set_permissions(guild.default_role, send_messages=True)
    await interaction.response.send_message("הטיקט שוחרר מ-freeze וכעת כולם יכולים לכתוב.", ephemeral=False)

# -----------------------
# Events
# -----------------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print("Bot is ready.")

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
#=================================================#
        webserver.keep_alive()
        bot.run(BOT_TOKEN)

