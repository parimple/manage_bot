from sqlalchemy import exists, desc
from models import *
from sqlalchemy.sql import func
from datasources import session


def get_top_members(amount):
    query = session.query(MemberScore.member_id, func.sum(MemberScore.score).label('sum_points')). \
        group_by(MemberScore.member_id).order_by(desc('sum_points')).all()
    return query[0:amount]


def get_top_roles(amount):
    query = session.query(Role.id).filter(Role.type == 'top').all()
    return query[0:amount]


def get_guild_date(guild_id):
    query = session.query(Guild.date).filter(Guild.id == guild_id).first()
    return query.date


def set_guild_date(guild_id, date):
    query = session.query(Guild).filter(Guild.id == guild_id).first()
    query.date = date
    return


def reset_points_global(day):
    (day_id,) = session.query(Score.id) \
        .filter(Score.name == day).first()
    session.query(MemberScore) \
        .filter(MemberScore.score_id == day_id) \
        .update({MemberScore.score: 0})
    return


def reset_points_by_id(member_id):
    session.query(MemberScore) \
        .filter(MemberScore.member_id == member_id) \
        .update({MemberScore.score: 0})
    return


def set_weeks():
    monday = Score(
        name='Monday',
        type='week'
    )
    tuesday = Score(
        name='Tuesday',
        type='week'
    )
    wednesday = Score(
        name='Wednesday',
        type='week'
    )
    thursday = Score(
        name='Thursday',
        type='week'
    )
    friday = Score(
        name='Friday',
        type='week'
    )
    saturday = Score(
        name='Saturday',
        type='week'
    )
    sunday = Score(
        name='Sunday',
        type='week'
    )
    session.add_all([monday, tuesday, wednesday, thursday, friday, saturday, sunday])


def check_role_by_type(role_type):
    query = session.query(exists().where(Role.type == role_type)).scalar()
    return query


def check_score_by_type(score_type):
    query = session.query(exists().where(Score.type == score_type)).scalar()
    return query


def set_role(role_id, role_name, role_type):
    role = Role(
        id=role_id,
        name=role_name,
        type=role_type,
    )
    session.add(role)
    session.commit()


def check_guild_by_id(guild_id):
    query = session.query(exists().where(Guild.id == guild_id)).scalar()
    return query


def set_guild_by_id(guild_id, date_now):
    guild = Guild(
        id=guild_id,
        date=date_now
    )
    session.add(guild)


def check_member(member_id):
    query = session.query(exists().where(Member.id == member_id)).scalar()
    return query


def set_member(member_id, member_name, member_discriminator):
    new_member = Member(
        id=member_id,
        username=member_name,
        discriminator=member_discriminator
    )
    session.add(new_member)


def set_member_scores(member_id, types):
    for score in session.query(Score).filter(Score.type.in_(types)):
        member_score = MemberScore(
            member_id=member_id,
            score_id=score.id,
            score=0
        )
        session.add(member_score)


def add_member_score(member_id, types, points):
    member_scores = session.query(MemberScore).join(Score).\
        filter((MemberScore.member_id == member_id) & (Score.name.in_(types))).all()
    for member_score in member_scores:
        member_score.score += points
