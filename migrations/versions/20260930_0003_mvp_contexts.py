"""Create identity, creative authoring and content library tables."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260930_0003"
down_revision: str | Sequence[str] | None = "20260930_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("parental_pin_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identity_users")),
    )
    op.create_index("ix_identity_users_email", "identity_users", ["email"], unique=True)

    op.create_table(
        "creative_characters",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("visual_description", sa.Text(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["identity_users.id"],
            name=op.f("fk_creative_characters_owner_id_identity_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_characters")),
    )
    op.create_index(
        "ix_creative_characters_owner_name", "creative_characters", ["owner_id", "name"]
    )

    op.create_table(
        "creative_scenarios",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("visual_description", sa.Text(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["identity_users.id"],
            name=op.f("fk_creative_scenarios_owner_id_identity_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_scenarios")),
    )
    op.create_index("ix_creative_scenarios_owner_name", "creative_scenarios", ["owner_id", "name"])

    op.create_table(
        "creative_style_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prompt_modifier", sa.Text(), nullable=False),
        sa.Column("visual_settings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["identity_users.id"],
            name=op.f("fk_creative_style_profiles_owner_id_identity_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_style_profiles")),
    )
    op.create_index(
        "ix_creative_style_profiles_owner_name", "creative_style_profiles", ["owner_id", "name"]
    )

    op.create_table(
        "creative_stories",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("style_profile_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["identity_users.id"],
            name=op.f("fk_creative_stories_owner_id_identity_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["creative_scenarios.id"],
            name=op.f("fk_creative_stories_scenario_id_creative_scenarios"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["style_profile_id"],
            ["creative_style_profiles.id"],
            name=op.f("fk_creative_stories_style_profile_id_creative_style_profiles"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_stories")),
    )
    op.create_index("ix_creative_stories_owner_title", "creative_stories", ["owner_id", "title"])

    op.create_table(
        "creative_story_pages",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("story_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("visual_config", sa.JSON(), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["creative_stories.id"],
            name=op.f("fk_creative_story_pages_story_id_creative_stories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_creative_story_pages")),
    )
    op.create_index(
        "uq_creative_story_pages_story_page_number",
        "creative_story_pages",
        ["story_id", "page_number"],
        unique=True,
    )

    op.create_table(
        "creative_story_page_characters",
        sa.Column("page_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("character_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["character_id"],
            ["creative_characters.id"],
            name=op.f("fk_creative_story_page_characters_character_id_creative_characters"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["page_id"],
            ["creative_story_pages.id"],
            name=op.f("fk_creative_story_page_characters_page_id_creative_story_pages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "page_id", "character_id", name=op.f("pk_creative_story_page_characters")
        ),
    )

    op.create_table(
        "content_library_items",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=10), nullable=False),
        sa.Column("resource_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("resource_path", sa.Text(), nullable=True),
        sa.Column("media_type", sa.String(length=120), nullable=True),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "item_type IN ('image', 'story', 'music')", name="ck_content_library_items_type"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["identity_users.id"],
            name=op.f("fk_content_library_items_owner_id_identity_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_content_library_items")),
    )
    op.create_index(
        "ix_content_library_owner_type", "content_library_items", ["owner_id", "item_type"]
    )
    op.create_index(
        "uq_content_library_owner_resource",
        "content_library_items",
        ["owner_id", "item_type", "resource_id"],
        unique=True,
    )

    with op.batch_alter_table("generation_jobs") as batch:
        batch.add_column(sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.create_foreign_key(
            "fk_generation_jobs_owner_id_identity_users",
            "identity_users",
            ["owner_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.create_index("ix_generation_jobs_owner_id", "generation_jobs", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_jobs_owner_id", table_name="generation_jobs")
    with op.batch_alter_table("generation_jobs") as batch:
        batch.drop_constraint("fk_generation_jobs_owner_id_identity_users", type_="foreignkey")
        batch.drop_column("owner_id")
    op.drop_index("uq_content_library_owner_resource", table_name="content_library_items")
    op.drop_index("ix_content_library_owner_type", table_name="content_library_items")
    op.drop_table("content_library_items")
    op.drop_table("creative_story_page_characters")
    op.drop_index("uq_creative_story_pages_story_page_number", table_name="creative_story_pages")
    op.drop_table("creative_story_pages")
    op.drop_index("ix_creative_stories_owner_title", table_name="creative_stories")
    op.drop_table("creative_stories")
    op.drop_index("ix_creative_style_profiles_owner_name", table_name="creative_style_profiles")
    op.drop_table("creative_style_profiles")
    op.drop_index("ix_creative_scenarios_owner_name", table_name="creative_scenarios")
    op.drop_table("creative_scenarios")
    op.drop_index("ix_creative_characters_owner_name", table_name="creative_characters")
    op.drop_table("creative_characters")
    op.drop_index("ix_identity_users_email", table_name="identity_users")
    op.drop_table("identity_users")
