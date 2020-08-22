import asyncio
from datetime import datetime, timedelta

import discord
from datasources.queries import *
import inspect
import datasources.models as models
import datasources.queries as queries
from mappings import BOT, GUILD, COMMANDS, MUSIC_PREFIX, MUSIC_COMMANDS, BONUS, CHANNELS, EMOJIS
from datasources import session, engine
from random import randint, choice
from functions import *
from colour import Color
import math

if not engine.dialect.has_table(engine, 'member'):
    models.Base.metadata.create_all(engine)

client = discord.Client()
invites = []
colors = {}
channels = {}
#x = datetime.now() - timedelta(hours=6)
#set_guild_date(560189268304330772, x)
#session.commit()
bot_datetime = get_guild_date(GUILD['id'])


@client.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    nsfw = guild.get_role(GUILD['video_ban'])
    private_category = guild.get_channel(GUILD['private_category'])
    private_category_p = guild.get_channel(GUILD['private_category_p'])
    if after.channel:
        if before.channel != after.channel:
            if after.channel.id in [GUILD['create_channel'], GUILD['create_channel_p']]:
                overwrite = get_member_permissions(member.id)
                permission_overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=overwrite.host_everyone_view_channel,
                                                                    connect=overwrite.host_everyone_connect,
                                                                    speak=overwrite.host_everyone_speak)
                }
                overwrite_guests = get_member_guests(member.id)
                for guest_id, view_channel, connect, speak in overwrite_guests:
                    guest = guild.get_member(guest_id)
                    if guest:
                        if all(p is None for p in [view_channel, connect, speak]):
                            continue
                        else:
                            permission_overwrites[guest] = discord.PermissionOverwrite(read_messages=view_channel,
                                                                                       connect=connect,
                                                                                       speak=speak)
                permission_overwrites[member] = discord.PermissionOverwrite(
                    read_messages=True,
                    connect=True,
                    speak=True,
                    move_members=False)
                permission_overwrites[nsfw] = discord.PermissionOverwrite(
                        stream=False)

                # chunks = math.ceil(len(permission_overwrites) / 95)
                # print('chunks', chunks)
                # overwrites_list = split_dict_equally(permission_overwrites, chunks)
                # from pprint import pprint
                # pprint(overwrites_list)
                first95 = {k: permission_overwrites[k] for k in list(permission_overwrites)[:95]}
                other_perms = {k: permission_overwrites[k] for k in list(permission_overwrites)[95:]}

                new_channel = await guild.create_voice_channel(
                    member.display_name,
                    category=after.channel.category,
                    bitrate=guild.bitrate_limit,
                    user_limit=overwrite.host_channel_limit,
                    overwrites=first95)

                await member.move_to(new_channel)
                channels[new_channel.id] = member.id

                for member, perms in other_perms.items():
                    await new_channel.set_permissions(member, overwrite=perms)
            elif after.channel.id == GUILD['afk_channel_id']:
                pass
            elif after.channel.id in CHANNELS:
                channel_name = choice(EMOJIS)+' private' if after.channel.id not in [696760847736766524, 715466140679143466] else choice(EMOJIS)+' public'
                permission_overwrites = {nsfw: discord.PermissionOverwrite(
                        stream=False)}
                new_channel = await guild.create_voice_channel(
                    channel_name,
                    category=after.channel.category,
                    bitrate=guild.bitrate_limit,
                    user_limit=CHANNELS[after.channel.id][1],
                    overwrites=permission_overwrites
                )
                try:
                    await member.move_to(new_channel)
                except (discord.errors.NotFound, discord.errors.HTTPException) as e:
                    pass

    if before.channel:
        if before.channel != after.channel:
            if (len(before.channel.members) == 0) and (before.channel.id not in CHANNELS):
                if before.channel.id in channels:
                    del channels[before.channel.id]
                try:
                    await before.channel.delete()
                except discord.errors.NotFound:
                    pass
            # elif before.channel


@client.event
async def on_member_join(member):
    member_hosts = get_member_hosts(member.id)
    guild = member.guild
    # print(member_hosts)
    if member_hosts:
        for host_id in member_hosts:
            print(host_id.speak, host_id.connect, host_id.view_channel)
            host = guild.get_member(host_id.member_host)
            if host:
                print(host)
                temp_channels = {k: v for k, v in channels.items() if v}
                for channel_id in temp_channels:
                    if host.id == temp_channels[channel_id]:
                        channel = guild.get_channel(channel_id)
                        await channel.set_permissions(member,
                                                      speak=host_id.speak,
                                                      connect=host_id.connect,
                                                      read_messages=host_id.view_channel)

    invites_old = invites.copy()
    invites.clear()
    invites.extend(await member.guild.invites())
    try:
        invite = discord.utils.find(lambda inv: inv.uses > discord.utils.get(invites_old, id=inv.id).uses, invites)
    except AttributeError:
        diff = list(set(invites) - set(invites_old))
        if len(diff) > 0:
            diff.sort(key=lambda inv: inv.created_at, reverse=True)
            invite = diff[0]
        else:
            invite = None

    if check_member(member.id) is False:
        if invite:
            set_member(member.id, member.name, member.discriminator, invite.inviter.id, datetime.now())
            inviter = member.guild.get_member(invite.inviter.id)
            if (member.joined_at - member.created_at) > timedelta(days=GUILD['join_days']):
                if inviter:
                    if not inviter.bot:
                        await inviter.add_roles(member.guild.get_role(GUILD['recruiter']), reason='recruiter')
                        if (member.joined_at - member.created_at) > timedelta(days=GUILD['join_days']):
                            invited_list = get_invited_list(inviter.id)
                            real_count = 0
                            for invited_id in invited_list:
                                invited = guild.get_member(invited_id)
                                if invited:
                                    if invited.avatar and (invited.joined_at -
                                                           invited.created_at) > timedelta(days=GUILD['join_days']):
                                        real_count += 1
                            if real_count > 1:
                                await inviter.add_roles(member.guild.get_role(GUILD['dj_id']), reason='dj')
                            if real_count > 3:
                                await inviter.add_roles(member.guild.get_role(GUILD['join_id']), reason='join')
                            if real_count > 7:
                                await inviter.add_roles(member.guild.get_role(GUILD['temp_bonus_id']), reason='bonus')
                            if real_count > 15:
                                await inviter.add_roles(member.guild.get_role(GUILD['bonus_id']), reason='bonus')
                            if real_count > 31:
                                pass
                            if (real_count > 63) and (real_count < 128):
                                if any(role.name == GUILD['colored_name'] for role in inviter.roles):
                                    pass
                                else:
                                    colored_role = await guild.create_role(name=GUILD['colored_name'])
                                    colored_role_position = guild.get_role(GUILD['colored_role_position'])
                                    print('role position', colored_role_position.position)
                                    await inviter.add_roles(colored_role, reason='colored')
                                    # await asyncio.sleep(10)
                                    await colored_role.edit(position=colored_role_position.position+1,reason='position')
                            if real_count > 127:
                                if any(role.name == GUILD['multi_colored_name'] for role in inviter.roles):
                                    pass
                                else:
                                    multi_colored_role = await guild.create_role(name=GUILD['multi_colored_name'])
                                    multi_colored_role_position = guild.get_role(GUILD['colored_role_position'])
                                    await inviter.add_roles(multi_colored_role, reason='multi_colored')
                                    # await asyncio.sleep(10)
                                    await multi_colored_role.edit(position=multi_colored_role_position.position+1,
                                                                  reason='position')
                            if real_count > 255:
                                await inviter.add_roles(member.guild.get_role(BONUS['bonus_1_id']), reason='bonus')
                            if real_count > 511:
                                await inviter.add_roles(member.guild.get_role(BONUS['bonus_2_id']), reason='bonus')
                            if real_count > 1023:
                                await inviter.add_roles(member.guild.get_role(BONUS['bonus_3_id']), reason='bonus')

        else:
            set_member(member.id, member.name, member.discriminator, None, datetime.now())
        session.commit()
        set_member_scores(member.id, ['week'])
        session.commit()
    join_logs = member.guild.get_channel(GUILD['join_logs_id'])
    if invite:
        await join_logs.send('member: {}, display_name: {}, inviter: {} <@{}>, invite_code: {}, uses: {}'
                             .format(member.mention, member.display_name, invite.inviter, invite.inviter.id,
                                     invite.code, invite.uses))
    else:
        await join_logs.send('member: {}, display_name: {}, inviter: {}'
                             .format(member.mention, member.display_name, None))


@client.event
async def on_message(message):
    message_save = message
    date_now = datetime.now()
    global bot_datetime
    guild = message.guild

    if bot_datetime.minute != date_now.minute:
        date_db = bot_datetime
        bot_datetime = date_now
        set_guild_date(GUILD['id'], date_now)
        session.commit()
        # guild = client.get_guild(GUILD['id'])

        invites_new = await guild.invites()
        diff = list(set(invites_new) - set(invites))
        if len(diff) > 0:
            invites.extend(diff)
        if date_now.minute % 15 == 0:
            first_role = guild.roles[1]
            if first_role.name in [GUILD['colored_name'], GUILD['multi_colored_name']]:
                colored_role_position = guild.get_role(GUILD['colored_role_position'])
                print('role position', colored_role_position.position)
                # await asyncio.sleep(10)
                await first_role.edit(position=colored_role_position.position + 1, reason='position')
            print(date_now, '15 min')
            for role in colors:
                if colors[role]:
                    await role.edit(colour=choice(colors[role]))
            # await client.change_presence(
            #     activity=discord.Game(name=choice(['> discord.gg/ZARjpB9 <', '< discord.gg/ZARjpB9 >'])))

            # private_category = guild.get_channel(GUILD['private_category'])
            for channel in guild.voice_channels:
                if (len(channel.members) < 1) and (channel.id not in CHANNELS):
                    if channels.get(channel.id):
                        del channels[channel.id]
                    await channel.delete()
                    continue

                for member in channel.members:
                    if (not member.bot) and (check_member(member.id) is False):
                        if (date_now - member.joined_at).seconds > 60:
                            set_member(member.id, member.name, member.discriminator, None, datetime.now())
                            session.commit()
                            set_member_scores(member.id, ['week'])
                            session.commit()
                    if member.voice.self_mute or member.voice.self_deaf or member.bot:
                        continue
                    else:
                        if len(channel.members) > 1:
                            add_member_score(member.id, date_now.strftime("%A"), 15)
                            session.commit()
                        else:
                            add_member_score(member.id, date_now.strftime("%A"), 2)
                            session.commit()

        if date_db.strftime("%A") != date_now.strftime("%A"):
            colors.clear()
            role_recruiter = guild.get_role(GUILD['recruiter'])
            role_patreon_4 = guild.get_role(GUILD['patreon_4_id'])
            for member in role_recruiter.members:
                await member.remove_roles(role_recruiter)

            role_temp_bonus = guild.get_role(GUILD['temp_bonus_id'])
            for member in role_temp_bonus.members:
                await member.remove_roles(role_temp_bonus)

            for role in guild.roles:
                if role.name == GUILD['colored_name'] or role.name == GUILD['multi_colored_name']:
                    if len(role.members) == 0:
                        await role.delete()
                    elif role.members.pop(0) not in role_patreon_4.members:
                        await role.delete()

            reset_points_global(date_now.strftime("%A"))

        if date_now.hour != date_db.hour:
            print(date_now, date_db, '1h update')
            role_everyone = guild.get_role(GUILD['fake_everyone_id'])
            role_here = guild.get_role(GUILD['fake_here_id'])
            for member in role_everyone.members:
                await member.remove_roles(role_everyone)
                await member.remove_roles(role_here)
            members_top = get_top_members(GUILD['top'])
            roles_top = get_top_roles(GUILD['top'])

            for (role_top_id,), member_top in zip(roles_top, members_top):
                role_top = guild.get_role(role_top_id)

                member_top_id, member_top_score = member_top
                member = guild.get_member(member_top_id)
                if member is None:
                    reset_points_by_id(member_top_id)
                    continue
                else:
                    for member_old in role_top.members:
                        if member_old.id == member.id:
                            continue
                        else:
                            await member_old.remove_roles(role_top, reason='top remove')
                    await member.add_roles(role_top, reason='top add')

    if not message.content:
        return

    if message.author.bot:
        return

    if message.role_mentions:
        await message.author.add_roles(message.guild.get_role(GUILD['fake_everyone_id']), reason='everyone ping')
        await message.author.add_roles(message.guild.get_role(GUILD['fake_here_id']), reason='here ping')

    args = message.content.split(' ')
    if len(message.content) < 2:
        return

    if message.channel.id != GUILD['bots_channel_id'] and len(args[0]) > 1 and \
            args[0][0] in MUSIC_PREFIX and args[0][1:].lower() in MUSIC_COMMANDS:
        try:
            await message.delete()
            return
        except discord.errors.NotFound:
            return

    for command in COMMANDS:
        if command in args[0].lower():
            return
    points = 0
    if len(args) > 32:
        to_add = 32
        points += to_add
    else:
        to_add = len(args)
        points += to_add

    for role_id in BONUS.values():
        role = message_save.guild.get_role(role_id)
        if (role in message_save.author.roles) and (randint(1, 100) < GUILD['rand_boost']):
            points += to_add

    # nitro_booster = message_save.guild.get_role(GUILD['nitro_booster_id'])
    # if (nitro_booster in message.author.roles) and (randint(1, 100) < GUILD['rand_boost']):
    #     points += len(args)
    # patreon_2 = message_save.guild.get_role(GUILD['patreon_2_id'])
    # if (patreon_2 in message.author.roles) and (randint(1, 100) < GUILD['rand_boost']):
    #     points += len(args)
    # temp_bonus = message_save.guild.get_role(GUILD['temp_bonus_id'])
    # if (temp_bonus in message.author.roles) and (randint(1, 100) < GUILD['rand_boost']):
    #     points += len(args)
    # bonus = message_save.guild.get_role(GUILD['bonus_id'])
    # if (bonus in message.author.roles) and (randint(1, 100) < GUILD['rand_boost']):
    #     points += len(args)

    if check_member(message.author.id) is False:
        if (date_now - message.author.joined_at).seconds > 60:
            set_member(message.author.id, message.author.name, message.author.discriminator, None, datetime.now())
            session.commit()
            set_member_scores(message.author.id, ['week'])
            session.commit()
    add_member_score(message.author.id, date_now.strftime("%A"), points)
    session.commit()

    parent_id = get_member_parent_id(message.author.id)

    if parent_id:
        if (check_member(parent_id)) and (randint(1, 100) < GUILD['rand_parent']):
            add_member_score(parent_id, date_now.strftime("%A"), points)
    session.commit()

    if not message.attachments and message.content[0] == BOT['prefix']:
        command = args.pop(0)[1:].lower()
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), message.author, command, args)
        if command in ['reset_color', 'rc']:
            for role in message.author.roles:
                if role.name == GUILD['multi_colored_name']:
                    colors[role] = []
        if command in ['color', 'colour']:
            if args:
                try:
                    color_string = ''.join(args)
                    if '#' in color_string:
                        color_string = color_string.replace('#', '')
                    new_color = Color(color_string)
                    print(new_color.hex_l)
                    hex_string = new_color.hex_l.replace('#', '')
                    discord_color = discord.Color(int(hex_string, 16))
                    for role in message.author.roles:
                        if role.name == GUILD['multi_colored_name']:
                            await role.edit(color=discord_color)
                            colors.setdefault(role, []).append(discord_color)
                        elif role.name == GUILD['colored_name']:
                            await role.edit(colour=discord_color)

                except ValueError as err:
                    print(err)
                    pass
                try:
                    color_string = ''.join(args)
                    if '#' in color_string:
                        color_string = color_string.replace('#', '')
                    discord_color = discord.Color(int(color_string, 16))
                    for role in message.author.roles:
                        if role.name == GUILD['multi_colored_name']:
                            await role.edit(colour=discord_color)
                            colors.setdefault(role, []).append(discord_color)
                        elif role.name == GUILD['colored_name']:
                            await role.edit(colour=discord_color)

                except ValueError:
                    pass

        if command in ['help', 'h']:
            embed = discord.Embed()
            embed.add_field(name='connect permission',
                            value='{}connect - <@{}>'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='view permission',
                            value='{}view - <@{}>'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='speak permission',
                            value='{}speak - <@{}>'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='reset permissions',
                            value='{}reset <@{}>'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='global connect permission',
                            value='{}connect -'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='global view permission',
                            value='{}view -'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='global speak permission',
                            value='{}speak -'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='reset global permissions',
                            value='{}reset'.format(BOT['prefix'], message.author.id), inline=True)
            embed.add_field(name='user limit',
                            value='{}limit 2'.format(BOT['prefix'], message.author.id), inline=True)
            embed.set_footer(text="to allow permission use +")

            await message.channel.send(embed=embed)
            return

        if command in ['p', 'profile']:
            if message.mentions:
                author = message.mentions[0]
                parent_id = get_member_parent_id(author.id)
            else:
                author = message.author
            inviter = message.guild.get_member(parent_id)
            if inviter is None:
                inviter_name = 'None'
            else:
                inviter_name = inviter.display_name
            invited_count = get_invited_count(author.id)
            invited_list = get_invited_list(author.id)
            real_count = 0
            for invited_id in invited_list:
                invited = message.guild.get_member(invited_id)
                if invited:
                    if invited.avatar and (invited.joined_at - invited.created_at) > timedelta(days=GUILD['join_days']):
                        real_count += 1
            roles_l = [role.name for role in author.roles]
            roles_l.pop(0)
            roles = ' '.join(roles_l) if len(roles_l) > 0 else '-'
            embed = discord.Embed()
            embed.set_author(name=author.name, icon_url=author.avatar_url)
            embed.add_field(name='created at', value=author.created_at.strftime("%d/%m/%Y\n%H:%M:%S"))
            embed.add_field(name='joined at', value=author.joined_at.strftime("%d/%m/%Y\n%H:%M:%S"))
            embed.add_field(name='roles', value=roles)
            embed.add_field(name='invited people', value="{}({})".format(real_count, invited_count), inline=True)
            embed.set_footer(text="invited by {}".format(inviter_name))
            await message.channel.send(embed=embed)
            return
        if command in ['speak', 's', 'connect', 'c', 'view', 'v', 'reset', 'r']:
            if (message.author not in message.author.guild.get_role(GUILD['join_id']).members) and \
                    (message.author not in message.author.guild.get_role(GUILD['nitro_booster_id']).members) and\
                    (message.author not in message.author.guild.get_role(GUILD['patreon_2_id']).members):
                print('nie ma')
                return
            if (len(args) < 1) and command not in ['reset', 'r']:
                return
            host = message.author
            if command in ['reset', 'r']:
                parameter = '+'
            else:
                parameter = args.pop(0)

            allowed = BOT['true'] + BOT['false']
            if parameter not in allowed:
                parameter = True
            else:
                if parameter in BOT['true']:
                    parameter = True
                elif parameter in BOT['false']:
                    parameter = False
            if message.mentions:
                guest = message.mentions[0]
            else:
                guest = None
            if guest:
                overwrites = get_member_member(host.id, guest.id)
                if not overwrites:
                    set_member_member(host.id, guest.id)
                    session.commit()
                    overwrites = get_member_member(host.id, guest.id)
                view_channel, connect, speak = overwrites
                if command in ['reset', 'r']:
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_ in temp_channels:
                        channel = guild.get_channel(channel_)
                        if host.id == temp_channels[channel.id]:
                            await channel.set_permissions(guest, overwrite=None)
                            if guest in channel.members:
                                afk_channel = message.guild.get_channel(GUILD['afk_channel_id'])
                                await guest.move_to(afk_channel)
                                await guest.move_to(channel)
                    update_member_member(host.id, guest.id, speak=None, connect=None, view_channel=None)
                    session.commit()
                elif command in ['speak', 's']:
                    permission_overwrites = discord.PermissionOverwrite(
                            read_messages=view_channel,
                            connect=connect,
                            speak=parameter)
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_ in temp_channels:
                        channel = guild.get_channel(channel_)
                        if host.id == temp_channels[channel.id]:
                            # await channel.set_permissions(guest, speak=parameter)
                            await channel.set_permissions(guest, overwrite=permission_overwrites)
                            print(guest.id)
                            print([member.id for member in channel.members])
                            if guest in channel.members:
                                print('jest')
                                afk_channel = message.guild.get_channel(GUILD['afk_channel_id'])
                                await guest.move_to(afk_channel)
                                print('move')
                                await guest.move_to(channel)
                                print('move2')
                    update_member_member(host.id, guest.id, speak=parameter)
                    session.commit()
                elif command in ['connect','c']:
                    permission_overwrites = discord.PermissionOverwrite(
                            read_messages=view_channel,
                            connect=parameter,
                            speak=speak)
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_ in temp_channels:
                        channel = guild.get_channel(channel_)
                        if host.id == temp_channels[channel.id]:
                            # await channel.set_permissions(guest, connect=parameter)
                            await channel.set_permissions(guest, overwrite=permission_overwrites)
                            if parameter is False:
                                if guest in channel.members:
                                    await guest.move_to(None)
                    update_member_member(host.id, guest.id, connect=parameter)
                    session.commit()
                elif command in ['view', 'v']:
                    permission_overwrites = discord.PermissionOverwrite(
                            read_messages=parameter,
                            connect=connect,
                            speak=speak)
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_ in temp_channels:
                        channel = guild.get_channel(channel_)
                        if host.id == temp_channels[channel.id]:
                            # await channel.set_permissions(guest, view_channel=parameter)
                            await channel.set_permissions(guest, overwrite=permission_overwrites)
                            if parameter is False:
                                if guest in channel.members:
                                    await guest.move_to(None)
                    update_member_member(host.id, guest.id, view_channel=parameter)
                    session.commit()
            else:
                if command in ['reset', 'r']:
                    create_channel = message.guild.get_channel(GUILD['create_channel'])
                    update_member(host.id, speak=True, view_channel=True, connect=True, limit=99)
                    update_member_members(host.id)
                    session.commit()
                    try:
                        await host.move_to(create_channel)
                    except discord.errors.HTTPException:
                        return
                elif command in ['speak', 's']:
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_id in temp_channels:
                        if host.id == temp_channels[channel_id]:
                            channel = guild.get_channel(channel_id)
                            await channel.set_permissions(message.guild.default_role, speak=parameter)
                    update_member(host.id, speak=parameter)
                    session.commit()
                elif command in ['connect', 'c']:
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_id in temp_channels:
                        if host.id == temp_channels[channel_id]:
                            channel = guild.get_channel(channel_id)
                            await channel.set_permissions(message.guild.default_role, connect=parameter)
                    update_member(host.id, connect=parameter)
                    session.commit()
                elif command in ['view', 'v']:
                    temp_channels = {k: v for k, v in channels.items() if v}
                    for channel_id in temp_channels:
                        if host.id == temp_channels[channel_id]:
                            channel = guild.get_channel(channel_id)
                            await channel.set_permissions(message.guild.default_role, view_channel=parameter)
                    update_member(host.id, view_channel=parameter)
                    session.commit()

        if command in ['limit', 'l']:
            if len(args) < 1:
                return
            host = message.author
            limit_str = args.pop(0)
            if limit_str.isdigit():
                limit = int(limit_str)
                if isinstance(limit, int):
                    if limit < 0:
                        limit = 0
                    elif limit > 99:
                        limit = 99
            else:
                return
            temp_channels = {k: v for k, v in channels.items() if v}
            for channel_id in temp_channels:
                if host.id == temp_channels[channel_id]:
                    channel = guild.get_channel(channel_id)
                    await channel.edit(user_limit=limit)
            update_member(host.id, limit=limit)
            session.commit()

        if GUILD['mod'] in [role.name for role in message.author.roles]:
            if command == "dc":
                if message.mentions and message.mentions[0].bot:
                    await message.mentions[0].move_to(None)

        if message.author.id == BOT['owner']:
            if command == 'inv':
                channel = message.guild.text_channels[0]
                inv = await channel.create_invite()
                await message.channel.send(inv)
            if command == 'new_date':
                set_guild_date(guild.id, datetime.now() - timedelta(hours=6))
                session.commit()
            if command == 'patreon':
                pass
            if command == 'ban':
                if message.mentions:
                    to_ban_id = message.mentions[0].id
                    # to_ban = message.mentions[0]
                    # print(to_ban)
                else:
                    to_ban_id = args.pop(0).strip('<@!>')
                    # to_ban = await client.fetch_user(to_ban_id)
                    # print(to_ban)
                to_ban = discord.Object(to_ban_id)
                print(to_ban)
                try:
                    await message.channel.send('<@{}> banned'.format(to_ban_id))
                    await message.guild.ban(to_ban)
                except discord.errors.NotFound:
                    pass

            if command in ['banall', 'ban_all']:
                if message.mentions:
                    inviter = message.mentions[0]
                else:
                    inviter_id = args.pop(0).strip('<@!>')
                    inviter = await client.fetch_user(inviter_id)
                ban_list = get_invited_list_minutes(inviter.id,
                                                    datetime.now() - timedelta(minutes=int(args.pop())))
                for member_id in ban_list:
                    # member = message.guild.get_member(member_id)
                    member = discord.Object(member_id)
                    print(member)
                    try:
                        await message.channel.send('<@{}> banned'.format(member_id))
                        await message.guild.ban(member)
                    except discord.errors.NotFound:
                        continue
            if command == 'showall':
                if message.mentions:
                    inviter = message.mentions[0]
                else:
                    inviter_id = args.pop(0).strip('<@!>')
                    inviter = await client.fetch_user(inviter_id)
                ban_list = get_invited_list(inviter.id)
                for member_id in ban_list:
                    # member = message.guild.get_member(member_id)
                    member = discord.Object(member_id)
                    print(member)
                    try:
                        if member.id in [member.id for member in message.guild.members]:
                            await message.channel.send('<@{}> invited'.format(member_id))
                        # await message.guild.ban(member)
                    except discord.errors.NotFound:
                        continue
            if command == 'eval':
                # try:
                code = cleanup_code(' '.join(args))
                evaled = eval(code)
                # print(type(evaled))
                if inspect.isawaitable(evaled):
                    await message.channel.send(await evaled)
                else:
                    await message.channel.send("```{}```".format(evaled))
                # except:
                #     print('eval except')
                # if type(evaled) !=
            if command == 'datetime':
                print(date_now.strftime("%A"))
            elif command == 'addNsfw':
                members = message.guild.members
                for member in members:
                    if (date_now - member.created_at).days < 14:
                        await member.add_roles(message.guild.get_role(GUILD['nsfw_id']), reason='nsfw new account')
            elif command == 'clearroles':
                for role in message.guild.roles:
                    if role.name in [GUILD['colored_name'], GUILD['multi_colored_name']]:
                        await role.delete()

            elif command == 'resetpoints':
                if len(args) > 0:
                    if message.mentions:
                        reset_points_by_id(message.mentions[0].id)
                    else:
                        reset_points_by_id(args[0])
                else:
                    print(message.content)
                return
            elif command == 'delTopRoles':
                top_roles = get_top_roles(128)
                for role_id, in top_roles:
                    print(role_id)
                    role = message.guild.get_role(role_id)
                    await role.delete()
                return
            elif command == 'say':
                await message.channel.send(' '.join(args))
                await message.delete()
            elif command == 'sayhc':
                message_old = await message.channel.fetch_message(592443154058182686)
                content = """
**Rangi numeryczne [1, 2, 3 … 128] na liście użytkowników. Co to jest?**
Jest to autorski system rankingu aktywności, stworzony na potrzeby tego serwera.

**Jak zdobyć własną rangę na liście użytkowników? Sposobów jest kilka:**
1. Aktywność na czacie tekstowym.
2. Przebywanie na kanałach głosowych.
3. Aktywność osób, które zostały przez Ciebie zaproszone (10% wygenerowanego ruchu pojawia się też na Twoim koncie)
4. Nitro Serwer Boost lub Patronite (https://www.patreon.com/zaGadka), zwiększają wszystkie pozostałe bonusy o 25%

**Co dostaniesz za zaproszenie nowej osoby na serwer?** (ilość zaproszonych osób `?profile`)
1+ osoba ♳ - czarny kolor nicku do końca dnia
2 osoby ♴ - DJ, czyli kontrola nad botami muzycznymi
4 osoby ♵ - możliwość tworzenia własnego kanału głosowego z możliwością mutowania (więcej komend: `?help`)
8+ osób ♶ - +25%  punktów do końca dnia
16 osób ♷ - +25% punktów na stałe
**32 osoby ✪ - osoba po uzyskaniu danej liczby zaproszeń, jest pierwszej kolejności brana pod uwagę, przy wyborze moderatora**
64+ osoby ♸ - indywidualna ranga, możesz zmieniać jej kolor za pomocą komendy np `?color light blue` do końca dnia
128+ osób ♹ - indywidualna ranga jak wyżej, z tą różnicą że cyklicznie zmienia ona wybrane przez Ciebie kolory
256 osób ⚀ -dostep do kanalu premium, +25% punktów na stałe
512, 1024, 2048 ⚁⚂⚃ - +25% punktów na stałe + **nitro** (lub równowartość pln)
+ oznacza, że w następnym dniu, rola się odświeży po dołączeniu jednej osoby

**Jak zmienić kolor nicku?**
1. Wybrać <a:zaGadkaRed:592406448302981149> <a:zaGadkaGreen:592406448315564062> <a:zaGadjaBlue:592406448386998289> za pomocą reakcji widocznych na samym dole
2. Aby otrzymać wyjątkowy kolor, należy zaprosić nową osobę (czarny), boostować serwer (czarny), być patronem ($2- czarny, $4- dowolny)"""
                await message_old.edit(content=content)
            elif command == 'everyone':
                await message.channel.send('@everyone')
                await message.delete()
            elif command == 'here':
                await message.channel.send('@here')
                await message.delete()
            elif command == 'rgb':
                message_rgb = await message.channel.send(GUILD['roles_rgb'])
                await message_rgb.delete()
                await message.delete()
            elif command == 'editMessage':
                message_old = await message.channel.fetch_message(args.pop(0))
                content = ' '.join(args)
                await message_old.edit(content=content)


@client.event
async def on_member_remove(member):
    leave_logs = member.guild.get_channel(GUILD['leave_logs_id'])
    await leave_logs.send('member: {}, display_name: {}'.format(member.mention, member.display_name))


@client.event
async def on_ready():
    date_now = datetime.now()
    guild = client.get_guild(GUILD['id'])
    invites.extend(await guild.invites())

    if check_score_by_type('week') is False:
        set_weeks()

    if check_role_by_type('top') is False:
        for i in range(1, GUILD['top'] + 1):
            print(i)
            role = await guild.create_role(name=i, hoist=True)
            set_role(role.id, i, 'top')
            session.commit()

    if check_guild_by_id(GUILD['id']) is False:
        set_guild_by_id(GUILD['id'], date_now)
    session.commit()

    # private_category = guild.get_channel(GUILD['private_category'])
    # for channel in private_category.channels:
    #     if channel.id != GUILD['create_channel']:
    #         await channel.delete()

    print(client.user.id)
    print(client.user.name)
    print('---------------')
    print('This bot is ready for action!')
    # client.loop.create_task(presence())


@client.event
async def on_invite_create(invite):
    print('invite created')
    invites.append(invite)

if __name__ == '__main__':
    try:
        client.run(BOT['token'])
    except Exception as e:
        print('Could Not Start Bot')
        print(e)
    finally:
        print('Closing Session')
        session.close()
