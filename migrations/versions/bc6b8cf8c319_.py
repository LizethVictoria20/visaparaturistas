"""empty message

Revision ID: bc6b8cf8c319
Revises: e73b300cfa02
Create Date: 2024-10-05 19:24:15.089247

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc6b8cf8c319'
down_revision = 'e73b300cfa02'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=100), nullable=False))
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
        batch_op.create_unique_constraint('uq_user_email', ['email'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)
        batch_op.drop_column('email')

    op.create_table('_alembic_tmp_user',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('username', sa.VARCHAR(length=100), nullable=False),
    sa.Column('password_hash', sa.VARCHAR(length=100), nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('email', sa.VARCHAR(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email', name='uq_user_email'),
    sa.UniqueConstraint('username')
    )
    # ### end Alembic commands ###
