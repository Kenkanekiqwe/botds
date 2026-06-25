import discord
from discord.ext import commands
import re
from collections import defaultdict
import datetime
import asyncio

# ===== ВСТАВЬТЕ ВАШ ТОКЕН ЗДЕСЬ =====
TOKEN = 'MTUxOTY3OTE0ODE2MjAyMzQ3NQ.GB2FSk.KzjC-kwlmwrUSlar_G-HZwrKCRvNJ-COP77268'

# ===== НАСТРОЙКИ =====
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.bans = True
intents.guilds = True
intents.moderation = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Словари для статистики
invite_counter = defaultdict(lambda: defaultdict(int))
ban_counter = defaultdict(lambda: defaultdict(int))

# Исключения (ID пользователей, которых не трогать)
EXCEPTIONS = []

# Настройки защиты
ANTI_DDOS_ENABLED = True
MAX_INVITES = 3
TIMEOUT_DURATION = 900  # 15 минут
MAX_BANS = 5

# Канал для управления и логов
ADMIN_CHANNEL_NAME = "anti-ddos"

# Список ID каналов для логов (заполняется автоматически)
LOG_CHANNELS = {}

@bot.event
async def on_ready():
    print('=' * 50)
    print(f'✅ Бот {bot.user} успешно запущен!')
    print(f'📊 Бот находится на {len(bot.guilds)} серверах')
    print('=' * 50)
    print('🛡️ Анти-Ддудос защита активна!')
    
    # Создаем канал для управления на каждом сервере
    for guild in bot.guilds:
        await create_admin_channel(guild)

async def create_admin_channel(guild):
    """Создает канал anti-ddos для владельца и администраторов"""
    try:
        # Проверяем, есть ли уже такой канал
        existing_channel = discord.utils.get(guild.channels, name=ADMIN_CHANNEL_NAME)
        
        if existing_channel:
            LOG_CHANNELS[guild.id] = existing_channel.id
            print(f'📌 Канал {ADMIN_CHANNEL_NAME} уже существует на сервере {guild.name}')
            
            # Обновляем права доступа у существующего канала
            await update_channel_permissions(guild, existing_channel)
            return
        
        # Создаем категорию для каналов бота
        category = discord.utils.get(guild.categories, name="🛡️ Anti-DDoS")
        if not category:
            category = await guild.create_category("🛡️ Anti-DDoS")
        
        # Настраиваем права доступа
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False,
                send_messages=False,
                read_messages=False,
                connect=False
            )
        }
        
        # Добавляем права для всех ролей с правами администратора
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,  # Не могут писать
                    read_messages=True,
                    read_message_history=True
                )
        
        # Права для владельца сервера (может писать)
        owner = guild.get_member(guild.owner_id)
        if owner:
            overwrites[owner] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True
            )
        
        # Права для самого бота
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_messages=True,
            read_message_history=True,
            manage_messages=True,
            manage_channels=True
        )
        
        # Создаем канал
        channel = await guild.create_text_channel(
            ADMIN_CHANNEL_NAME,
            category=category,
            overwrites=overwrites,
            topic="🛡️ Управление анти-ддудос защитой | Только владелец может управлять, админы только читают"
        )
        
        LOG_CHANNELS[guild.id] = channel.id
        
        # Отправляем приветственное сообщение
        embed = discord.Embed(
            title='🛡️ Anti-DDoS Control Panel',
            description='**Добро пожаловать в панель управления анти-ддудос защитой!**',
            color=discord.Color.green()
        )
        embed.add_field(
            name='👑 Права доступа',
            value='• **Владелец сервера** может управлять ботом\n'
                  '• **Администраторы** могут только просматривать логи\n'
                  '• **Остальные** не видят этот канал',
            inline=False
        )
        embed.add_field(
            name='📊 Текущие настройки',
            value=f'`Статус:` {"✅ Включена" if ANTI_DDOS_ENABLED else "❌ Выключена"}\n'
                  f'`Лимит приглашений:` {MAX_INVITES}\n'
                  f'`Таймаут:` {TIMEOUT_DURATION//60} минут\n'
                  f'`Лимит банов:` {MAX_BANS}\n'
                  f'`Исключения:` {len(EXCEPTIONS)} пользователей',
            inline=False
        )
        embed.add_field(
            name='💡 Команды (только для владельца)',
            value='`!antiddos on` - Включить\n'
                  '`!antiddos off` - Выключить\n'
                  '`!antiddos add @user` - Добавить в исключения\n'
                  '`!antiddos remove @user` - Убрать из исключений\n'
                  '`!antiddos friend` - Список исключений\n'
                  '`!antiddos set_invites <число>` - Лимит приглашений\n'
                  '`!antiddos set_bans <число>` - Лимит банов\n'
                  '`!antiddos status` - Статус',
            inline=False
        )
        embed.set_footer(text=f'Создано {datetime.datetime.now().strftime("%d.%m.%Y %H:%M")}')
        
        await channel.send(embed=embed)
        print(f'✅ Создан канал {ADMIN_CHANNEL_NAME} на сервере {guild.name}')
        
    except Exception as e:
        print(f'❌ Ошибка создания канала: {e}')

async def update_channel_permissions(guild, channel):
    """Обновляет права доступа у существующего канала"""
    try:
        # Обновляем права для всех ролей
        for role in guild.roles:
            if role.permissions.administrator:
                await channel.set_permissions(
                    role,
                    view_channel=True,
                    send_messages=False,
                    read_messages=True,
                    read_message_history=True
                )
        
        # Права для владельца
        owner = guild.get_member(guild.owner_id)
        if owner:
            await channel.set_permissions(
                owner,
                view_channel=True,
                send_messages=True,
                read_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True
            )
        
        # Скрываем канал для всех остальных
        await channel.set_permissions(
            guild.default_role,
            view_channel=False,
            send_messages=False,
            read_messages=False
        )
        
        print(f'✅ Обновлены права доступа для канала {channel.name}')
        
    except Exception as e:
        print(f'❌ Ошибка обновления прав: {e}')

async def log_action(guild, title, description, color=discord.Color.blue(), fields=None):
    """Отправляет лог в канал anti-ddos"""
    try:
        channel_id = LOG_CHANNELS.get(guild.id)
        if not channel_id:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel:
            return
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.utcnow()
        )
        
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        
        embed.set_footer(text=f'Сервер: {guild.name}')
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f'❌ Ошибка отправки лога: {e}')

@bot.event
async def on_message(message):
    global ANTI_DDOS_ENABLED
    
    # Пропускаем сообщения ботов и если защита выключена
    if message.author.bot or not ANTI_DDOS_ENABLED:
        await bot.process_commands(message)
        return
    
    # Проверка исключений
    if message.author.id in EXCEPTIONS:
        await bot.process_commands(message)
        return
    
    # Проверка на приглашения (discord.gg И discord.com)
    invites = re.findall(r'(?:discord\.gg|discord\.com)/[^\s]+', message.content)
    
    if invites and message.guild:
        user_id = message.author.id
        guild_id = message.guild.id
        
        invite_counter[guild_id][user_id] += len(invites)
        
        if invite_counter[guild_id][user_id] > MAX_INVITES:
            try:
                await message.author.timeout(
                    discord.utils.utcnow() + datetime.timedelta(seconds=TIMEOUT_DURATION),
                    reason="Спам приглашениями"
                )
                await message.channel.send(
                    f'⏰ {message.author.mention} отправлен в таймаут на {TIMEOUT_DURATION//60} минут за спам приглашениями!'
                )
                invite_counter[guild_id][user_id] = 0
                
                # Логируем действие
                await log_action(
                    message.guild,
                    '⏰ Таймаут выдан',
                    f'{message.author.mention} отправлен в таймаут за спам приглашениями',
                    discord.Color.orange(),
                    [
                        ('Пользователь', message.author.mention, True),
                        ('Приглашений', str(len(invites)), True),
                        ('Длительность', f'{TIMEOUT_DURATION//60} минут', True)
                    ]
                )
                
            except Exception as e:
                print(f'❌ Ошибка таймаута: {e}')
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    """Отслеживание добавления новых ботов на сервер и автоматический бан"""
    if not ANTI_DDOS_ENABLED:
        return
    
    # Проверяем, является ли новый участник ботом
    if member.bot:
        # Проверяем, кто добавил бота через audit log
        async for entry in member.guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
            if entry.target.id == member.id:
                moderator = entry.user
                
                # Проверяем, не в исключениях ли тот, кто добавил
                if moderator and not moderator.bot and moderator.id not in EXCEPTIONS:
                    try:
                        # 1. Снимаем все роли с того, кто добавил бота
                        mod_member = member.guild.get_member(moderator.id)
                        if mod_member:
                            await mod_member.edit(roles=[], reason="Добавление бота на сервер")
                        
                        # 2. БАНИМ добавленного бота
                        await member.guild.ban(
                            member,
                            reason="Автоматический бан бота (анти-ддудос защита)",
                            delete_message_days=1
                        )
                        
                        # 3. Отправляем сообщение в общий чат
                        channel = member.guild.system_channel
                        if channel:
                            embed = discord.Embed(
                                title='🛡️ Анти-Ддудос Защита',
                                description=f'**Бот был автоматически забанен!**',
                                color=discord.Color.red()
                            )
                            embed.add_field(
                                name='👤 Кто добавил',
                                value=f'{moderator.mention} (`{moderator.id}`)',
                                inline=True
                            )
                            embed.add_field(
                                name='🤖 Добавленный бот',
                                value=f'{member.mention} (`{member.id}`)',
                                inline=True
                            )
                            embed.add_field(
                                name='⚡ Действие',
                                value='• Сняты все роли с добавившего\n• Бот забанен',
                                inline=False
                            )
                            await channel.send(embed=embed)
                        
                        # 4. Логируем в канал anti-ddos
                        await log_action(
                            member.guild,
                            '🤖 Бот забанен',
                            f'Бот {member.mention} был автоматически забанен',
                            discord.Color.red(),
                            [
                                ('Кто добавил', moderator.mention, True),
                                ('Бот', member.mention, True),
                                ('Действие', 'Сняты роли + Бан', True)
                            ]
                        )
                            
                    except discord.Forbidden:
                        channel = member.guild.system_channel
                        if channel:
                            await channel.send(
                                f'❌ У меня нет прав банить ботов или снимать роли с {moderator.mention}!'
                            )
                    except Exception as e:
                        print(f'❌ Ошибка при бане бота: {e}')
                break

@bot.event
async def on_member_ban(guild, user):
    if not ANTI_DDOS_ENABLED or user.id in EXCEPTIONS:
        return
    
    async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
        if entry.target.id == user.id:
            moderator = entry.user
            if moderator and not moderator.bot and moderator.id not in EXCEPTIONS:
                ban_counter[guild.id][moderator.id] += 1
                
                if ban_counter[guild.id][moderator.id] > MAX_BANS:
                    try:
                        member = guild.get_member(moderator.id)
                        if member:
                            await member.edit(roles=[], reason="Превышен лимит банов")
                            channel = guild.system_channel
                            if channel:
                                await channel.send(
                                    f'⚠️ {moderator.mention} превысил лимит банов ({MAX_BANS})! Все роли сняты.'
                                )
                            ban_counter[guild.id][moderator.id] = 0
                            
                            # Логируем действие
                            await log_action(
                                guild,
                                '⚠️ Снятие ролей',
                                f'{moderator.mention} превысил лимит банов',
                                discord.Color.red(),
                                [
                                    ('Модератор', moderator.mention, True),
                                    ('Лимит банов', str(MAX_BANS), True),
                                    ('Всего банов', str(ban_counter[guild.id][moderator.id] + 1), True)
                                ]
                            )
                            
                    except Exception as e:
                        print(f'❌ Ошибка снятия ролей: {e}')
            break

@bot.command(name='antiddos')
async def antiddos(ctx, action=None, *, user=None):
    global ANTI_DDOS_ENABLED, MAX_INVITES, MAX_BANS
    
    # Проверяем, является ли пользователь владельцем сервера
    if ctx.author.id != ctx.guild.owner_id:
        await ctx.send('❌ Эта команда доступна только **владельцу сервера**!')
        return
    
    if action is None:
        embed = discord.Embed(
            title='🛡️ Анти-Ддудос Защита',
            description=f'**Статус:** {"✅ Включена" if ANTI_DDOS_ENABLED else "❌ Выключена"}',
            color=discord.Color.blue()
        )
        embed.add_field(
            name='Настройки',
            value=f'`Сколько ссылок:` {MAX_INVITES}\n`Таймаут:` {TIMEOUT_DURATION//60} мин\n`После скольки банов снимает все роли:` {MAX_BANS}\n`На кого бот не действует:` {len(EXCEPTIONS)}',
            inline=False
        )
        embed.add_field(
            name='Команды',
            value='`!antiddos on` - Включить\n`!antiddos off` - Выключить\n`!antiddos add @user` - Добавить в исключения\n`!antiddos remove @user` - Убрать из исключений\n`!antiddos friend` - Список исключений\n`!antiddos set_invites <число>` - Лимит приглашений\n`!antiddos set_bans <число>` - Лимит банов\n`!antiddos status` - Статус',
            inline=False
        )
        await ctx.send(embed=embed)
        
        # Логируем действие
        await log_action(
            ctx.guild,
            '📋 Просмотр настроек',
            f'{ctx.author.mention} просмотрел настройки',
            discord.Color.blue(),
            [
                ('Пользователь', ctx.author.mention, True),
                ('Статус', 'Включена' if ANTI_DDOS_ENABLED else 'Выключена', True)
            ]
        )
        return
    
    if action == 'on':
        ANTI_DDOS_ENABLED = True
        await ctx.send('✅ Анти-Ддудос защита **включена**!')
        
        await log_action(
            ctx.guild,
            '🟢 Защита включена',
            f'{ctx.author.mention} включил анти-ддудос защиту',
            discord.Color.green(),
            [('Пользователь', ctx.author.mention, True)]
        )
        return
    
    elif action == 'off':
        ANTI_DDOS_ENABLED = False
        await ctx.send('❌ Анти-Ддудос защита **выключена**!')
        
        await log_action(
            ctx.guild,
            '🔴 Защита выключена',
            f'{ctx.author.mention} выключил анти-ддудос защиту',
            discord.Color.red(),
            [('Пользователь', ctx.author.mention, True)]
        )
        return
    
    elif action == 'add':
        # Проверяем упоминания разными способами
        member = None
        
        # Способ 1: Если пользователь передан как аргумент
        if user:
            try:
                # Пробуем получить пользователя по имени
                member = await commands.MemberConverter().convert(ctx, user)
            except:
                pass
        
        # Способ 2: Если есть упоминания в сообщении
        if not member and ctx.message.mentions:
            member = ctx.message.mentions[0]
        
        # Способ 3: Если есть ID пользователя
        if not member and user and user.isdigit():
            try:
                member = ctx.guild.get_member(int(user))
            except:
                pass
        
        if member:
            if member.id not in EXCEPTIONS:
                EXCEPTIONS.append(member.id)
                await ctx.send(f'✅ {member.mention} добавлен в исключения!')
                
                await log_action(
                    ctx.guild,
                    '➕ Добавлен в исключения',
                    f'{member.mention} добавлен в белый список',
                    discord.Color.green(),
                    [
                        ('Добавил', ctx.author.mention, True),
                        ('Пользователь', member.mention, True),
                        ('Всего в списке', str(len(EXCEPTIONS)), True)
                    ]
                )
            else:
                await ctx.send(f'⚠️ {member.mention} уже в исключениях!')
        else:
            await ctx.send('❌ Не удалось найти пользователя! Упомяните его через @ или напишите ID.')
        return
    
    elif action == 'remove':
        # Проверяем упоминания разными способами
        member = None
        
        # Способ 1: Если пользователь передан как аргумент
        if user:
            try:
                member = await commands.MemberConverter().convert(ctx, user)
            except:
                pass
        
        # Способ 2: Если есть упоминания в сообщении
        if not member and ctx.message.mentions:
            member = ctx.message.mentions[0]
        
        # Способ 3: Если есть ID пользователя
        if not member and user and user.isdigit():
            try:
                member = ctx.guild.get_member(int(user))
            except:
                pass
        
        if member:
            if member.id in EXCEPTIONS:
                EXCEPTIONS.remove(member.id)
                await ctx.send(f'✅ {member.mention} убран из исключений!')
                
                await log_action(
                    ctx.guild,
                    '➖ Убран из исключений',
                    f'{member.mention} убран из белого списка',
                    discord.Color.orange(),
                    [
                        ('Убрал', ctx.author.mention, True),
                        ('Пользователь', member.mention, True),
                        ('Всего в списке', str(len(EXCEPTIONS)), True)
                    ]
                )
            else:
                await ctx.send(f'⚠️ {member.mention} не в исключениях!')
        else:
            await ctx.send('❌ Не удалось найти пользователя! Упомяните его через @ или напишите ID.')
        return
    
    elif action == 'friend':
        """Показывает список пользователей в белом списке"""
        if not EXCEPTIONS:
            embed = discord.Embed(
                title='👥 Белый список (Исключения)',
                description='📭 **Список пуст!**\n\nДобавьте пользователей командой:\n`!antiddos add @user`',
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Создаем список пользователей
        user_list = []
        for user_id in EXCEPTIONS:
            member = ctx.guild.get_member(user_id)
            if member:
                user_list.append(f'• {member.mention} (`{member.id}`)')
            else:
                user_list.append(f'• Пользователь с ID: `{user_id}` (не найден на сервере)')
        
        # Разбиваем список на страницы (по 10 пользователей)
        pages = []
        for i in range(0, len(user_list), 10):
            page = '\n'.join(user_list[i:i+10])
            pages.append(page)
        
        # Создаем embed
        embed = discord.Embed(
            title='👥 Белый список (Исключения)',
            description=f'Всего в списке: **{len(EXCEPTIONS)}** пользователей\n\n{pages[0]}',
            color=discord.Color.green()
        )
        embed.set_footer(text=f'Страница 1/{len(pages)}')
        
        await ctx.send(embed=embed)
        return
    
    elif action == 'set_invites':
        try:
            value = int(ctx.message.content.split()[2])
            if value > 0:
                MAX_INVITES = value
                await ctx.send(f'✅ Лимит приглашений: **{MAX_INVITES}**')
                
                await log_action(
                    ctx.guild,
                    '⚙️ Изменен лимит приглашений',
                    f'{ctx.author.mention} установил лимит приглашений на **{MAX_INVITES}**',
                    discord.Color.blue(),
                    [('Новое значение', str(MAX_INVITES), True)]
                )
            else:
                await ctx.send('❌ Число должно быть больше 0!')
        except:
            await ctx.send('❌ Укажите число! Пример: `!antiddos set_invites 3`')
        return
    
    elif action == 'set_bans':
        try:
            value = int(ctx.message.content.split()[2])
            if value > 0:
                MAX_BANS = value
                await ctx.send(f'✅ Лимит банов: **{MAX_BANS}**')
                
                await log_action(
                    ctx.guild,
                    '⚙️ Изменен лимит банов',
                    f'{ctx.author.mention} установил лимит банов на **{MAX_BANS}**',
                    discord.Color.blue(),
                    [('Новое значение', str(MAX_BANS), True)]
                )
            else:
                await ctx.send('❌ Число должно быть больше 0!')
        except:
            await ctx.send('❌ Укажите число! Пример: `!antiddos set_bans 5`')
        return
    
    elif action == 'status':
        embed = discord.Embed(
            title='📊 Статус Анти-Ддудос защиты',
            color=discord.Color.green() if ANTI_DDOS_ENABLED else discord.Color.red()
        )
        embed.add_field(name='Статус', value='✅ Включена' if ANTI_DDOS_ENABLED else '❌ Выключена', inline=True)
        embed.add_field(name='Лимит приглашений', value=str(MAX_INVITES), inline=True)
        embed.add_field(name='Таймаут', value=f'{TIMEOUT_DURATION//60} минут', inline=True)
        embed.add_field(name='Лимит банов', value=str(MAX_BANS), inline=True)
        embed.add_field(name='Исключения', value=f'{len(EXCEPTIONS)} пользователей', inline=True)
        await ctx.send(embed=embed)
        return
    
    else:
        await ctx.send('❌ Неизвестная команда! Используйте `!antiddos`')
        return

# ===== ЗАПУСК =====
if __name__ == '__main__':
    print('Запуск Анти-Ддудос бота...')
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'Ошибка: {e}')
        input('Нажмите Enter для выхода...')
