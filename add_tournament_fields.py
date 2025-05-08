
from models import db, Tournament
from sqlalchemy import Column, String

def upgrade():
    with db.engine.connect() as connection:
        connection.execute('ALTER TABLE tournaments ADD COLUMN about TEXT')
        connection.execute('ALTER TABLE tournaments ADD COLUMN draw_url TEXT')
        connection.execute('ALTER TABLE tournaments ADD COLUMN schedule_url TEXT')

if __name__ == '__main__':
    upgrade()
