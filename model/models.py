from .db_connector import Base
from sqlalchemy import Column,Integer,String,DateTime,Numeric

class User(Base):
    __tablename__ = 'tbl_user'
    __table_args__ = {"schema": "chata"}

    user_id = Column('user_id',Integer, primary_key=True)
    user_internal_id = Column('user_internal_id',String(100),nullable=False)
    user_email_address = Column('user_email_address',String(200),nullable=False)
    user_created_date = Column('user_created_date',DateTime,nullable=False)
    user_disabled_flg = Column('user_disabled_flg',Integer,nullable=False,default=0)

    def __repr__(self):
        return f'User : {self.user_email_address} - {self.user_internal_id}'

class ChatUploads(Base):
    __tablename__ = 'tbl_chat_upload'
    __table_args__ = {"schema": "chata"}

    upload_id =  Column('upload_id',Integer,primary_key=True)
    upload_title = Column('upload_title',String)
    upload_location = Column('upload_location', String)
    upload_date = Column('upload_date',DateTime)
    upload_user_id = Column('upload_user_id',Integer)
    processed_date = Column('processed_date',DateTime)
    delete_flag = Column('delete_flag',Integer,default=0)

class ChatDetail(Base):
    __tablename__ = 'tbl_chat_detail'
    __table_args__ = {"schema": "chata"}

    record_id = Column('record_id',Integer,primary_key=True)
    upload_id = Column('upload_id',Integer)
    member_phone = Column('member_phone',String)
    chat_time = Column('chat_time',DateTime)
    chat_message = Column('chat_message',String)
    has_url = Column('has_url',Integer)
    has_media = Column('has_media',Integer)
    word_count = Column('word_count',Integer)

class OtherEvents(Base):
    __tablename__ = 'tbl_chat_other_events'
    __table_args__ = {"schema": "chata"}

    record_id = Column('record_id',Integer,primary_key=True)
    upload_id = Column('upload_id',Integer)
    member_phone = Column('member_phone',String)
    event_time = Column('event_time',DateTime)
    event_type = Column('event_type',String)