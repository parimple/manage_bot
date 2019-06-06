#!/usr/local/Cellar/python/3.6.5_1/bin/python3
import asyncio
from datetime import datetime

import discord
from sqlalchemy import create_engine, exists, desc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql import func

import datasources.models
import datasources.queries
from mappings import BOT, GUILD

engine = create_engine('sqlite:///data/zagadka.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()


if not engine.dialect.has_table(engine, 'member'):
    datasources.models.Base.metadata.create_all(engine)

client = discord.Client()
now = datetime.now()
day = now.strftime("%A")


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
        guild_db = session.query(datasources.models.Guild).filter(datasources.models.Guild.id == GUILD['id']).first()
        now_loop = datetime.now()
        now_db = guild_db.date
        # print('datetime.now: ', now_loop)
        # print('guild_db.date.now: ', now_db)

        if now_db.strftime("%A") != now_loop.strftime("%A"):
            print(now_db)
            (day_id,) = session.query(datasources.models.Score.id)\
                .filter(datasources.models.Score.name == now_loop.strftime("%A")).first()

            session.query(datasources.models.MemberScore)\
                .filter(datasources.models.MemberScore.score_id == day_id)\
                .update({datasources.models.MemberScore.score: 0})
        if now_db.hour != now_loop.hour:
            top_members = session.query(datasources.models.MemberScore.member_id,
                                        func.sum(datasources.models.MemberScore.score).label('sum_points')).\
                group_by(datasources.models.MemberScore.member_id).order_by(desc('sum_points')).all()
            top_roles = session.query(datasources.models.Role).filter(datasources.models.Role.type == 'top').all()
            n = 0
            m = 0
            for top_role_db in top_roles:
                m += top_role_db.limit
                print(n, m, top_role_db)

                top_role_dc = guild.get_role(top_role_db.id)
                for member in top_role_dc.members:
                    await member.remove_roles(top_role_dc, reason='1h reset')
                # print(top_members[n:m])
                for member_db in top_members[n:m]:
                    # print(member_db)
                    member = guild.get_member(member_db.member_id)
                    print(member, top_role_dc)
                    # await member.add_roles(top_role_dc, reason='1h reset')

                n += top_role_db.limit
                print(n)

            print('---')

        guild_db.date = now_loop
        session.commit()
        await asyncio.sleep(60)


@client.event
async def on_ready():
    guild = client.get_guild(GUILD['id'])
#    print(now.)
    if not session.query(exists().where(datasources.models.Score.type == 'week')).scalar():
        monday = datasources.models.Score(
            name='Monday',
            type='week'
        )
        tuesday = datasources.models.Score(
            name='Tuesday',
            type='week'
        )
        wednesday = datasources.models.Score(
            name='Wednesday',
            type='week'
        )
        thursday = datasources.models.Score(
            name='Thursday',
            type='week'
        )
        friday = datasources.models.Score(
            name='Friday',
            type='week'
        )
        saturday = datasources.models.Score(
            name='Saturday',
            type='week'
        )
        sunday = datasources.models.Score(
            name='Sunday',
            type='week'
        )
        all_score = datasources.models.Score(
            name='AllScore',
            type='all_score'
        )
        session.add_all([monday, tuesday, wednesday, thursday, friday, saturday, sunday, all_score])
        session.commit()
    if not session.query(exists().where(datasources.models.Role.type == 'topx')).scalar():
        if not discord.utils.get(guild.roles, name='1'):
            for i in range(4):
                role = await guild.create_role(name=i+1, hoist=True)
                print(role)


            # await guild.create_role(name='top002', hoist=True)
            # await guild.create_role(name='top004', hoist=True)
            # await guild.create_role(name='top008', hoist=True)
            # await guild.create_role(name='topBan')
            # await guild.create_role(name='top016', hoist=True)

        # top002 = discord.utils.get(guild.roles, name='top002')
        # top004 = discord.utils.get(guild.roles, name='top004')
        # top008 = discord.utils.get(guild.roles, name='top008')
        # spam = discord.utils.get(guild.roles, name='spam')
        # top016 = discord.utils.get(guild.roles, name='top016')
        # print(top002)
        # r_spam = Role(
        #     id=spam.id,
        #     name=spam.name,
        #     type='punishment'
        # )
        #
        # r_top002 = Role(
        #     id=top002.id,
        #     name='top002',
        #     type='top',
        #     limit=2
        # )
        # r_top004 = Role(
        #     id=top004.id,
        #     name='top004',
        #     type='top',
        #     limit=4,
        #     parent_id=top002.id
        # )
        # r_top008 = Role(
        #     id=top008.id,
        #     name='top008',
        #     type='top',
        #     limit=8,
        #     parent_id=top004.id
        # )

        # r_top016 = Role(
        #     id=top016.id,
        #     name='top016',
        #     type='top',
        #     limit=16,
        #     parent_id=top008.id
        # )

        # session.add_all([r_top002, r_top004, r_top008, r_spam])
        # session.commit()
    if not session.query(exists().where(datasources.models.Guild.id == GUILD['id'])).scalar():
        guild1 = datasources.models.Guild(
            id=guild.id,
            date=now
        )
        session.add(guild1)
        session.commit()

    print(client.user.id)
    print(client.user.name)
    print('---------------')
    print('This bot is ready for action!')
    client.loop.create_task(presence())
    client.loop.create_task(minute())


@client.event
async def on_message(message):

    if message.author.bot:
        return

    args = message.content.split(' ')
    if len(args) < 1:
        return

    try:
        member = session.query(datasources.models.Member) \
            .filter(datasources.models.Member.id == message.author.id).one()
    except MultipleResultsFound as multiple:
        print(multiple)
    except NoResultFound:
        new_member = datasources.models.Member(
            id=message.author.id,
            username=message.author.name,
            discriminator=message.author.discriminator
        )
        session.add(new_member)
        session.commit()

    try:
        member_score_day = session.query(datasources.models.MemberScore).join(datasources.models.Score) \
            .filter((datasources.models.MemberScore.member_id == message.author.id) & (datasources.models.Score.name == day)).one()
        member_score_all = session.query(datasources.models.MemberScore).join(datasources.models.Score) \
            .filter((datasources.models.MemberScore.member_id == message.author.id) & (datasources.models.Score.name == 'AllScore')).one()
        member_score_day.score += len(args)
        member_score_all.score += len(args)
        session.commit()
    except MultipleResultsFound as multiple:
        print(multiple)
    except NoResultFound as noResult:
        for score in session.query(datasources.models.Score).filter(datasources.models.Score.type.in_(['week', 'all_score'])):
            member_score = datasources.models.MemberScore(
                member_id=message.author.id,
                score_id=score.id,
                score=0
            )
            session.add(member_score)
            session.commit()
    if message.content:
        if message.author.id == BOT['owner'] and message.content[0] == BOT['prefix'] and len(args) > 0:
            args2 = message.content[1:]
            if args2 == 'dateTime':
                print(now.strftime("%A"))

            if args2 == 'initScore':
                monday = datasources.models.Score(
                    name='Monday',
                    type='week'
                )
                tuesday = datasources.models.Score(
                    name='Tuesday',
                    type='week'
                )
                wednesday = datasources.models.Score(
                    name='Wednesday',
                    type='week'
                )
                thursday = datasources.models.Score(
                    name='Thursday',
                    type='week'
                )
                friday = datasources.models.Score(
                    name='Friday',
                    type='week'
                )
                saturday = datasources.models.Score(
                    name='Saturday',
                    type='week'
                )
                sunday = datasources.models.Score(
                    name='Sunday',
                    type='week'
                )
                all_score = datasources.models.Score(
                    name='AllScore',
                    type='all_score'
                )
                session.add_all([monday, tuesday, wednesday, thursday, friday, saturday, sunday, all_score])
                return session.commit()

if __name__ == '__main__':
    try:
        client.run(BOT['token'])
    except Exception as e:
        print('Could Not Start Bot')
        print(e)
    finally:
        print('Closing Session')
        session.close()
