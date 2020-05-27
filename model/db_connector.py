from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import appconfig

db_engine = create_engine(appconfig.db_url,echo=True,pool_size=2, max_overflow=0)
Base = declarative_base()
Session = sessionmaker(bind = db_engine)

def get_session():
    #db_session = Session()
    #db_session.begin()
    return Session()