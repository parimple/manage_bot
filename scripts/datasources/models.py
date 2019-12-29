from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.sqlite import DATETIME, INTEGER, TEXT, BOOLEAN
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MemberScore(Base):
    __tablename__ = 'member_score'
    member_id = Column(INTEGER, ForeignKey('member.id'), primary_key=True)
    score_id = Column(INTEGER, ForeignKey('score.id'), primary_key=True)
    score = Column(INTEGER)


class MemberMember(Base):
    __tablename__ = 'member_member'
    member_host = Column(INTEGER, ForeignKey('member.id'), primary_key=True)
    member_guest = Column(INTEGER, ForeignKey('member.id'), primary_key=True)
    view_channel = Column(BOOLEAN)
    connect = Column(BOOLEAN)
    speak = Column(BOOLEAN)


class MemberRole(Base):
    __tablename__ = 'member_role'
    member_id = Column(INTEGER, ForeignKey('member.id'), primary_key=True)
    role_id = Column(INTEGER, ForeignKey('role.id'), primary_key=True)


class ChannelRole(Base):
    __tablename__ = 'channel_role'
    channel_id = Column(INTEGER, ForeignKey('channel.id'), primary_key=True)
    role_id = Column(INTEGER, ForeignKey('role.id'), primary_key=True)
    active = Column(BOOLEAN)


class Guild(Base):
    __tablename__ = 'guild'
    id = Column(INTEGER, primary_key=True, nullable=False)
    date = Column(DATETIME)


class Role(Base):
    __tablename__ = 'role'
    id = Column(INTEGER, primary_key=True, nullable=False)
    name = Column(TEXT)
    type = Column(TEXT)
    parent_id = Column(INTEGER, ForeignKey('role.id'))
    parent = relationship('Role', remote_side=[id])


class Score(Base):
    __tablename__ = 'score'
    id = Column(INTEGER, primary_key=True, nullable=False)
    name = Column(TEXT)
    type = Column(TEXT)


class Channel(Base):
    __tablename__ = 'channel'
    id = Column(INTEGER, primary_key=True, nullable=False)
    name = Column(TEXT)
    type = Column(TEXT)


class Member(Base):
    __tablename__ = 'member'
    id = Column(INTEGER, primary_key=True, nullable=False)
    username = Column(TEXT)
    discriminator = Column(TEXT)
    parent_id = Column(INTEGER, ForeignKey('member.id'))
    parent = relationship('Member', remote_side=[id])
    host_everyone_view_channel = Column(BOOLEAN)
    host_everyone_connect = Column(BOOLEAN)
    host_everyone_speak = Column(BOOLEAN)
    host_channel_limit = Column(INTEGER)

