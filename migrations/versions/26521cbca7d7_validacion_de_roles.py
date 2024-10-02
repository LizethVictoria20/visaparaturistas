"""Validacion de roles

Revision ID: 26521cbca7d7
Revises: ff43aaba5950
Create Date: 2024-10-02 15:52:23.032603

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = '26521cbca7d7'
down_revision = 'ff43aaba5950'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar si la tabla 'role' existe antes de intentar eliminarla
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    if 'role' in inspector.get_table_names():
        op.drop_table('role')
    
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=50), nullable=False))
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
        
        # Añadir nombre a la restricción única
        batch_op.create_unique_constraint('uq_roles_slug', ['slug'])

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('roles', schema=None) as batch_op:
        batch_op.drop_constraint('uq_roles_slug', type_='unique')
        batch_op.alter_column('name',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
        batch_op.drop_column('slug')

    op.create_table('role',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('name', sa.VARCHAR(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    # ### end Alembic commands ###
