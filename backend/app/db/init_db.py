"""Database initialization script for Forge 1."""

import logging

from sqlalchemy.orm import Session

from .models import Tenant, User, MarketplaceTemplate, ToolManifest
from .session import SessionLocal, create_tables

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Initialize the database with tables and initial data."""
    try:
        # Create tables
        create_tables()
        logger.info("Database tables created successfully")

        # Create initial data (dev only)
        import os
        if os.getenv("ENV", "dev") == "dev":
            db = SessionLocal()
            try:
                create_initial_data(db)
                logger.info("Initial data created successfully (dev)")
            finally:
                db.close()
        else:
            logger.info("Skipping demo data creation (ENV != dev)")

        # Test hygiene: when running under pytest, clear transient feature flags to
        # avoid cross-test contamination when pointing at a persistent local DB.
        try:
            import os

            if os.getenv("PYTEST_CURRENT_TEST"):
                from sqlalchemy.exc import SQLAlchemyError
                from .session import SessionLocal as _SL
                from app.core.flags.feature_flags import FeatureFlag

                with _SL() as _s:
                    try:
                        # Ensure table exists then clear
                        FeatureFlag.__table__.create(bind=_s.get_bind(), checkfirst=True)
                        _s.query(FeatureFlag).delete()
                        _s.commit()
                        logger.info("Cleared feature_flags table for test isolation")
                    except SQLAlchemyError:
                        _s.rollback()
        except Exception:
            # Best-effort only
            pass

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def create_initial_data(db: Session) -> None:
    """Create initial data for the application."""
    # Ensure default tenant exists
    default_tenant_id = "default"
    existing_tenant = db.get(Tenant, default_tenant_id)
    if existing_tenant is None:
        tenant = Tenant(id=default_tenant_id, name="Default Tenant")
        db.add(tenant)
        db.commit()
        logger.info("Created default tenant")

    # In dev only, create a default admin user if none exists
    import os as _os
    if _os.getenv("ENV", "dev") == "dev":
        if db.query(User).first():
            logger.info("Database already has data, skipping user initialization")
        else:
            admin_user = User(
                email="admin@forge1.com",
                username="admin",
                hashed_password="admin",  # In development only
                is_active=True,
                is_superuser=True,
                role="admin",
                tenant_id=default_tenant_id,
            )
            db.add(admin_user)
            db.commit()
            logger.info("Created default admin user: admin@forge1.com")

        # Seed marketplace templates (idempotent)
        try:
            MarketplaceTemplate.__table__.create(bind=db.get_bind(), checkfirst=True)
            existing_keys = {r.key for r in db.query(MarketplaceTemplate).all()}
            seeds = [
                ("lead_qualifier", "Lead Qualifier", "sales", "Qualify inbound leads", ["api_caller", "csv_reader"], {}),
                ("research_analyst", "Research Analyst", "research", "Research topics and summarize", ["web_scraper", "csv_writer"], {}),
                ("cs_agent", "Customer Support Agent", "support", "Handle support queries", ["api_caller", "slack_notifier"], {}),
                ("data_cleaner", "Data Cleaner", "ops", "Clean and normalize CSV data", ["csv_reader", "csv_writer"], {}),
                ("invoice_processor", "Invoice Processor", "finance", "Extract invoice data", ["api_caller"], {}),
                ("recruiter_sourcer", "Recruiter Sourcer", "hr", "Source candidates and outreach", ["api_caller", "csv_writer"], {}),
                ("social_copywriter", "Social Copywriter", "marketing", "Draft social posts", ["api_caller"], {}),
                ("reporting_analyst", "Reporting Analyst", "analytics", "Build weekly reports", ["csv_reader", "csv_writer"], {}),
            ]
            for key, name, vert, desc, tools, default in seeds:
                if key not in existing_keys:
                    db.add(
                        MarketplaceTemplate(
                            key=key,
                            name=name,
                            vertical=vert,
                            description=desc,
                            required_tools=tools,
                            default_config=default or {},
                            version="1.0",
                            enabled=True,
                        )
                    )
            db.commit()
        except Exception:
            db.rollback()
        # Seed tool manifests (idempotent)
        try:
            ToolManifest.__table__.create(bind=db.get_bind(), checkfirst=True)
            existing = {r.name for r in db.query(ToolManifest).all()}
            manifests = [
                ToolManifest(
                    name="csv_reader",
                    version="1.0",
                    scopes=["files:read"],
                    config_schema={
                        "type": "object",
                        "properties": {"delimiter": {"type": "string", "default": ","}},
                        "required": [],
                    },
                    docs_url="https://docs.local/tools/csv",
                ),
                ToolManifest(
                    name="csv_writer",
                    version="1.0",
                    scopes=["files:write"],
                    config_schema={
                        "type": "object",
                        "properties": {"delimiter": {"type": "string", "default": ","}},
                        "required": [],
                    },
                    docs_url="https://docs.local/tools/csv",
                ),
                ToolManifest(
                    name="slack_notifier",
                    version="1.0",
                    scopes=["slack:send"],
                    config_schema={
                        "type": "object",
                        "properties": {"webhook_url": {"type": "string"}},
                        "required": ["webhook_url"],
                    },
                    docs_url="https://api.slack.com/messaging/webhooks",
                ),
                ToolManifest(
                    name="excel_reader",
                    version="1.0",
                    scopes=["files:read"],
                    config_schema={"type": "object", "properties": {}, "required": []},
                    docs_url="https://docs.local/tools/excel",
                ),
                ToolManifest(
                    name="excel_writer",
                    version="1.0",
                    scopes=["files:write"],
                    config_schema={"type": "object", "properties": {}, "required": []},
                    docs_url="https://docs.local/tools/excel",
                ),
                ToolManifest(
                    name="gmail_imap",
                    version="0.1",
                    scopes=["email:read"],
                    config_schema={"type": "object", "properties": {"imap_url": {"type": "string"}}, "required": []},
                    docs_url="https://docs.local/tools/gmail_imap",
                ),
                ToolManifest(
                    name="ms_teams",
                    version="0.1",
                    scopes=["teams:send"],
                    config_schema={"type": "object", "properties": {"webhook_url": {"type": "string"}}, "required": []},
                    docs_url="https://learn.microsoft.com/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook",
                ),
                ToolManifest(
                    name="gdrive",
                    version="0.1",
                    scopes=["drive:read", "drive:write"],
                    config_schema={"type": "object", "properties": {}, "required": []},
                    docs_url="https://developers.google.com/drive/api",
                ),
            ]
            for m in manifests:
                if m.name not in existing:
                    db.add(m)
            db.commit()
        except Exception:
            db.rollback()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
