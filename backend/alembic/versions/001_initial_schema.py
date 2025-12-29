"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE stake_status AS ENUM ('PENDING', 'ACTIVE', 'SETTLED')")
    op.execute("CREATE TYPE settlement_type AS ENUM ('RETURNED', 'DONATED')")
    op.execute("CREATE TYPE processing_status AS ENUM ('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED')")
    
    # Create users table
    op.create_table('users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('clerk_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('clerk_id')
    )
    
    # Create stakes table
    op.create_table('stakes',
        sa.Column('stake_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount_eth', postgresql.NUMERIC(precision=18, scale=8), nullable=False),
        sa.Column('transaction_hash', sa.String(length=66), nullable=False),
        sa.Column('contract_stake_id', sa.Integer(), nullable=True),
        sa.Column('status', postgresql.ENUM('PENDING', 'ACTIVE', 'SETTLED', name='stake_status'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('settlement_type', postgresql.ENUM('RETURNED', 'DONATED', name='settlement_type'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('stake_id')
    )
    
    # Create pdf_uploads table
    op.create_table('pdf_uploads',
        sa.Column('upload_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('processing_status', postgresql.ENUM('UPLOADED', 'PROCESSING', 'COMPLETED', 'FAILED', name='processing_status'), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ),
        sa.PrimaryKeyConstraint('upload_id')
    )
    
    # Create quizzes table
    op.create_table('quizzes',
        sa.Column('quiz_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stake_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('questions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('user_answers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['stake_id'], ['stakes.stake_id'], ),
        sa.PrimaryKeyConstraint('quiz_id')
    )


def downgrade() -> None:
    op.drop_table('quizzes')
    op.drop_table('pdf_uploads')
    op.drop_table('stakes')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS processing_status")
    op.execute("DROP TYPE IF EXISTS settlement_type")
    op.execute("DROP TYPE IF EXISTS stake_status")