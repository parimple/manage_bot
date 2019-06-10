#!/usr/local/Cellar/python/3.6.5_1/bin/python3
import asyncio
from datetime import datetime

import discord
from queries import *
import datasources.models
import datasources.queries
from mappings import BOT, GUILD
from datasources import session, engine

if not engine.dialect.has_table(engine, 'member'):
    datasources.models.Base.metadata.create_all(engine)

client = discord.Client()


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

        if date_db.strftime("%A") != date_now.strftime("%A"):
            reset_points_global(date_now.strftime("%A"))

        if date_now.hour == date_db.hour:
            members_top = get_top_members(GUILD['top'])
            roles_top = get_top_roles(GUILD['top'])

            for role_top, member_top in zip(roles_top, members_top):


        set_guild_date(GUILD['id'], date_now)
        session.commit()
        await asyncio.sleep(60)


@client.event
async def on_ready():
    date_now = datetime.now()
    guild = client.get_guild(GUILD['id'])
    if check_score_by_type('week') is False:
        set_weeks()

    if check_role_by_type('top') is False:
        for i in range(1, GUILD['top']+1):
            role = await guild.create_role(name=i, hoist=True)
            set_role(role.id, i, 'top')

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
async def on_message(message):
    date_now = datetime.now()
    if message.author.bot:
        return

    args = message.content.split(' ')
    if len(args) < 1:
        return

    points = 0
    if len(args) > 32:
        points += 32
    else:
        points += len(args)

    if check_member(message.author.id) is False:
        set_member(message.author.id, message.author.name, message.author.discriminator)
        session.commit()
        set_member_scores(message.author.id, ['week', 'all_score'])
        session.commit()

    add_member_score(message.author.id, [date_now.strftime("%A"), 'AllScore'], points)
    session.commit()

    if message.content:
        if message.author.id == BOT['owner'] and message.content[0] == BOT['prefix'] and len(args) > 0:
            args2 = message.content[1:]
            if args2 == 'dateTime':
                print(date_now.strftime("%A"))


if __name__ == '__main__':
    try:
        client.run(BOT['token'])
    except Exception as e:
        print('Could Not Start Bot')
        print(e)
    finally:
        print('Closing Session')
        session.close()
