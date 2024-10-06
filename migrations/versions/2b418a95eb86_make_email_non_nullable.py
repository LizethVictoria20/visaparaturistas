from alembic import op
import sqlalchemy as sa

# Revisión de migración y dependencias
revision = '2b418a95eb86'
down_revision = 'd737305b58cb'
branch_labels = None
depends_on = None

def upgrade():
    # Añadir la columna 'email'
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=100), nullable=True))
    
    # Actualizar los valores de email a un valor por defecto
    op.execute("UPDATE user SET email = 'default@example.com' WHERE email IS NULL")
    
    # Alterar la columna para que no acepte valores nulos
    with op.batch_alter_table('user') as batch_op:
        batch_op.alter_column('email', nullable=False)

def downgrade():
    # Revertir los cambios eliminando la columna 'email'
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('email')
