import asyncio
from datetime import datetime

import discord
from queries import *
import datasources.models
import datasources.queries
from mappings import BOT, GUILD, COMMANDS
from datasources import session, engine
from random import randint

if not engine.dialect.has_table(engine, 'member'):
    datasources.models.Base.metadata.create_all(engine)

client = discord.Client()
invites = []


async def presence():
    while True:
        await client.change_presence(activity=discord.Game(name='R'))
        await asyncio.sleep(8)
        await client.change_presence(activity=discord.Game(name='G'))
        await asyncio.sleep(8)
        await client.change_presence(activity=discord.Game(name='B'))
        await asyncio.sleep(8)


async def minute():
    while True:
        guild = client.get_guild(GUILD['id'])
        date_db = get_guild_date(GUILD['id'])
        date_now = datetime.now()

        invites_new = await guild.invites()
        diff = list(set(invites_new) - set(invites))
        if len(diff) > 0:
            invites.extend(diff)

        if date_db.strftime("%A") != date_now.strftime("%A"):
            reset_points_global(date_now.strftime("%A"))
            role_everyone = guild.get_role(GUILD['fake_everyone_id'])
            role_here = guild.get_role(GUILD['fake_here_id'])
            for member in role_everyone.members:
                await member.remove_roles(role_everyone)
                await member.remove_roles(role_here)

        if date_now.hour != date_db.hour:
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

        set_guild_date(GUILD['id'], date_now)
        session.commit()
        await asyncio.sleep(60)


@client.event
async def on_member_join(member):
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
        set_member(member.id, member.name, member.discriminator, invite.inviter.id)
        session.commit()
        set_member_scores(member.id, ['week'])
        session.commit()
    join_logs = member.guild.get_channel(GUILD['join_logs_id'])
    await join_logs.send('member: {}, display_name: {}, inviter: {}'
                         .format(member.mention, member.display_name, invite.inviter))


@client.event
async def on_message(message):
    date_now = datetime.now()

    if not message.content:
        return

    if message.author.bot:
        return

    if message.role_mentions:
        await message.author.add_roles(message.guild.get_role(GUILD['fake_everyone_id']), reason='everyone ping')
        await message.author.add_roles(message.guild.get_role(GUILD['fake_here_id']), reason='here ping')

    args = message.content.split(' ')

    for command in COMMANDS:
        if command in args[0]:
            return

    points = 0
    if len(args) > 32:
        points += 32
    else:
        points += len(args)

    if check_member(message.author.id) is False:
        if (date_now-message.author.joined_at).seconds > 60:
            set_member(message.author.id, message.author.name, message.author.discriminator, None)
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
        command = args.pop(0)[1:]

        if command == 'profile':
            inviter = message.guild.get_member(parent_id)
            if inviter is None:
                inviter_name = 'None'
            else:
                inviter_name = inviter.display_name
            invited_count = get_invited_count(message.author.id)
            embed = discord.Embed()
            embed.add_field(name='invited people', value=invited_count, inline=True)
            embed.set_footer(text="invited by {}".format(inviter_name))
            await message.channel.send(embed=embed)
            return

        if message.author.id == BOT['owner']:
            if command == 'dateTime':
                print(date_now.strftime("%A"))
            elif command == 'addNsfw':
                members = message.guild.members
                for member in members:
                    if (date_now - member.created_at).days < 14:
                        await member.add_roles(message.guild.get_role(GUILD['nsfw_id']), reason='nsfw new account')

            elif command == 'resetPoints':
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
            elif command == 'e':
                await message.channel.send('@everyone')
                await message.delete()
            elif command == 'rgb':
                message_rgb = await message.channel.send(GUILD['roles_rgb'])
                await message_rgb.delete()
                await message.delete()


@client.event
async def on_ready():
    date_now = datetime.now()
    guild = client.get_guild(GUILD['id'])
    invites.extend(await guild.invites())

    if check_score_by_type('week') is False:
        set_weeks()

    if check_role_by_type('top') is False:
        for i in range(1, GUILD['top']+1):
            role = await guild.create_role(name=i, hoist=True)
            set_role(role.id, i, 'top')
            session.commit()

    if check_guild_by_id(GUILD['id']) is False:
        set_guild_by_id(GUILD['id'], date_now)
    session.commit()

    print(client.user.id)
    print(client.user.name)
    print('---------------')
    print('This bot is ready for action!')
    client.loop.create_task(presence())
    client.loop.create_task(minute())


@client.event
async def on_member_remove(member):
    leave_logs = member.guild.get_channel(GUILD['leave_logs_id'])
    await leave_logs.send('member: {}, display_name: {}'.format(member.mention, member.display_name))

if __name__ == '__main__':
    try:
        client.run(BOT['token'])
    except Exception as e:
        print('Could Not Start Bot')
        print(e)
    finally:
        print('Closing Session')
        session.close()
